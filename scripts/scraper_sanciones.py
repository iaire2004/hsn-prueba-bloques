#!/usr/bin/env python3
"""
scraper_sanciones.py — Boletines de Novedades del HSN → data/sanciones.json
=============================================================================
Consulta el endpoint de datos abiertos con el listado de Boletines de
Novedades (uno por sesión), descarga en memoria el PDF de cada boletín nuevo
y extrae, por tabla (pdfplumber `extract_tables`), los ítems de las secciones:
  - PROYECTOS DE LEY                                          -> "ley"
  - PROYECTOS DE DECRETO, RESOLUCIÓN, COMUNICACIÓN Y DECLARACIÓN
                                                    -> "decreto_res_com_dec"
  - ACUERDOS CONSIDERADOS                                      -> "acuerdo"
  - MOCIONES DE PREFERENCIA (solo resultado APROBADA)          -> "preferencia"
Las demás secciones (Cuestiones de privilegio, Ingreso acuerdos, Cambio de
giro, Homenajes, Diarios de sesiones, Elección de autoridades) se ignoran.

Es incremental: lee data/sanciones_procesados.json (lista de números de
boletín ya procesados, ej. "3/26") y sólo baja/parsea los boletines nuevos.
Acumula los ítems extraídos en data/sanciones.json.

Tolerante a fallos: si falla la descarga o el parseo de un boletín (o de una
fila puntual), se registra el error y se continúa con lo demás.

Variables de entorno opcionales:
    TEST               "1" para modo de prueba: procesa un único boletín
                        (el más reciente no procesado), imprime resultados
                        y no toca data/sanciones.json ni sanciones_procesados.json.
    SANCIONES_MIN_ANIO  año mínimo (de la fecha de sesión) a considerar;
                        default 2025 (el listado completo va hasta 2004).
"""

import json
import logging
import os
import re
import sys
import time
from io import BytesIO

try:
    import requests
    import pdfplumber
except ImportError:
    print("ERROR: faltan dependencias. Ejecutá: pip install -r requirements.txt")
    sys.exit(1)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
SANCIONES_JSON = os.path.join(DATA_DIR, "sanciones.json")
PROCESADOS_JSON = os.path.join(DATA_DIR, "sanciones_procesados.json")

TEST = os.getenv("TEST", "") == "1"
MIN_ANIO = int(os.getenv("SANCIONES_MIN_ANIO", "2025"))

URL_LISTADO = "https://www.senado.gob.ar/micrositios/DatosAbiertos/ExportarListadoBoletinNovedades/json"

# Ver nota en scraper_agenda.py: un User-Agent de navegador dispara el
# anti-bots del sitio; uno propio y honesto pasa sin problema. NO cambiarlo
# por uno de navegador.
HEADERS = {
    "User-Agent": "HSN-SistemaLegislativo/1.0 (+https://github.com/bonifaciomariano/hsn-sistema-legislativo)",
    "Accept": "application/json,text/html,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}

PAUSA_ENTRE_REQUESTS = 1.0

# Expediente: "S-289/26", "PE-98/26", "CD-20/24" (origen puede traer puntos: "P.E-133/26")
RE_EXP = re.compile(r"\b([A-ZÑ.]{1,5}-\s?\d+/\d{2})\b")  # tolera "S- 1442/26"

# En MOCIONES DE PREFERENCIA cada fila arranca con "Apellido: <expediente(s)...>"
# -> el apellido de quien solicitó la preferencia.
RE_SOLICITANTE = re.compile(r"^\s*([A-ZÁÉÍÓÚÑa-záéíóúñ][^:]{1,40}):")

# Encabezados de secciones a ignorar por completo (título de sección, no de columnas)
HEADERS_IGNORAR = (
    "CUESTIONES DE PRIVILEGIO",
    "INGRESO ACUERDOS",
    "CAMBIO DE GIRO",
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def obtener_listado_boletines():
    """Descarga y parsea el listado de boletines. El JSON del endpoint trae
    comas colgantes (no es JSON estricto) -> se limpia con regex antes de
    parsear."""
    r = requests.get(URL_LISTADO, headers=HEADERS, timeout=30)
    r.raise_for_status()
    limpio = re.sub(r",(\s*[}\]])", r"\1", r.text)
    data = json.loads(limpio)
    filas = data.get("table", {}).get("rows", [])

    boletines = []
    for fila in filas:
        nro_raw = (fila.get("NUMERO BOLETIN") or "").strip()
        fecha = (fila.get("FECHA SESION") or "").strip()
        url = (fila.get("URL") or "").strip()
        if not nro_raw or not url:
            continue
        nro_boletin = nro_raw.replace("-", "/", 1)
        try:
            anio = int(fecha.split("-")[0])
        except (ValueError, IndexError):
            anio = None
        if anio is not None and anio < MIN_ANIO:
            continue
        boletines.append({"nro_boletin": nro_boletin, "fecha_sesion": fecha, "url": url})
    return boletines


def cargar_procesados():
    if not os.path.exists(PROCESADOS_JSON):
        return set()
    with open(PROCESADOS_JSON, "r", encoding="utf-8") as f:
        return set(json.load(f))


def guardar_procesados(procesados):
    with open(PROCESADOS_JSON, "w", encoding="utf-8") as f:
        json.dump(sorted(procesados), f, ensure_ascii=False, indent=2)


def cargar_sanciones():
    if not os.path.exists(SANCIONES_JSON):
        return []
    with open(SANCIONES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_sanciones(items):
    with open(SANCIONES_JSON, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def norm_celda(c):
    return " ".join((c or "").split())


def extraer_expedientes(texto):
    encontrados = []
    for m in RE_EXP.finditer(texto or ""):
        origen, resto = m.group(1).split("-", 1)
        encontrados.append(f"{origen.replace('.', '')}-{resto.strip()}")
    return encontrados


def parsear_od_nro(celda):
    m = re.match(r"\s*(\d+)", celda or "")
    return int(m.group(1)) if m else None


def detectar_header(celdas):
    """Devuelve ('section', nombre_o_None) si la fila es un encabezado de
    sección o de columnas; None si es una fila de datos a procesar."""
    c0 = celdas[0].upper() if celdas else ""

    if celdas == ["OD", "ACUERDOS CONSIDERADOS", "RESULTADO", "OBSERVACIONES"]:
        return ("section", "acuerdo")
    if c0.startswith("MOCIONES DE PREFERENCIA"):
        return ("section", "preferencia")
    if c0 == "PROYECTOS DE LEY":
        return ("section", "ley")
    if c0.startswith("PROYECTOS DE DECRETO"):
        return ("section", "decreto_res_com_dec")
    if any(c0.startswith(h) for h in HEADERS_IGNORAR):
        return ("section", None)
    if c0 in ("OD", "N° DE EXPEDIENTE", "NRO DE EXPEDIENTE", "N DE EXPEDIENTE"):
        return ("col_header", None)
    return None


def procesar_fila(celdas, seccion, nro_boletin, fecha_sesion):
    solicitante = None
    if seccion == "preferencia":
        if len(celdas) < 3:
            return []
        texto, resultado, observaciones = celdas[0], celdas[1], celdas[2]
        if resultado.strip().upper() != "APROBADA":
            return []
        od_nro = None
        m = RE_SOLICITANTE.match(texto)
        if m:
            solicitante = norm_celda(m.group(1))
    else:
        if len(celdas) < 4:
            return []
        od_celda, texto, resultado, observaciones = celdas[0], celdas[1], celdas[2], celdas[3]
        od_nro = None if od_celda.strip().upper() == "S/T" else parsear_od_nro(od_celda)

    items = []
    for exp in expedientes_texto(texto):  # entiende citas combinadas: "S-252 y 308/26", "S-1808 y S-1497/25"
        item = {
            "expediente": exp,
            "od_nro": od_nro,
            "resultado": resultado,
            "observaciones": observaciones,
            "seccion": seccion,
            "fecha_sesion": fecha_sesion,
            "nro_boletin": nro_boletin,
        }
        if solicitante:
            item["solicitante"] = solicitante
        items.append(item)
    return items


def parsear_boletin(pdf_bytes, nro_boletin, fecha_sesion):
    items = []
    errores = []
    seccion_actual = None
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for pagina in pdf.pages:
                try:
                    tablas = pagina.extract_tables()
                except Exception as e:
                    errores.append(f"extract_tables falló en una página: {e}")
                    continue
                for tabla in tablas:
                    for fila in tabla:
                        try:
                            celdas = [norm_celda(c) for c in fila]
                            marca = detectar_header(celdas)
                            if marca is not None:
                                if marca[0] == "section":
                                    seccion_actual = marca[1]
                                continue
                            if not seccion_actual:
                                continue
                            items.extend(procesar_fila(celdas, seccion_actual, nro_boletin, fecha_sesion))
                        except Exception as e:
                            errores.append(f"fila en sección {seccion_actual}: {e}")
    except Exception as e:
        errores.append(f"apertura/lectura del PDF falló: {e}")
    if not items:
        # Formato nuevo (sin tablas): reintentar leyendo el texto corrido.
        items_t, errores_t = parsear_boletin_texto(pdf_bytes, nro_boletin, fecha_sesion)
        if items_t:
            log.info("    (formato texto: %d ítems)", len(items_t))
        return items_t, errores + errores_t
    return items, errores


# ── Formato "texto" (boletines nuevos, p.ej. 9/26): sin tablas ─────────────
# Desde cierto boletín el PDF ya no trae tablas: cada ítem es texto corrido
#   OD 402: Dictamen en el proyecto de ley ... (CD-3/26)
#   APROBADO - Ley 27.828.
# precedido por el encabezado de comisiones ("Comisiones de X y de Y:") y
# dentro de secciones numeradas ("5. PROYECTOS DE LEY").
RE_SECCION_TXT = re.compile(r"^\d+\.\s+(.+?)\s*$")
RE_RESULTADO_TXT = re.compile(r"^(APROBAD|RECHAZAD|RETIRAD|SANCION|ARCHIV|QUEDA)[A-ZÁÉÍÓÚÑ]*\b")
RE_ENTRADA_OD = re.compile(r"^(?:OD|O\.D\.)\s*(\d+)\s*:\s*(.*)$", re.I)
RE_ENTRADA_ST = re.compile(r"^S/T\s*:\s*(.*)$", re.I)
RE_EXP_INICIO = re.compile(r"^[A-ZÑ.]{1,5}-\d+(?:/\d{2}|\s*(?:,|y)\s*\d+/\d{2})")
RE_PIE_TXT = re.compile(r"^(BOLET[IÍ]N DE NOVEDADES|DIRECCI[OÓ]N GENERAL DE COMISIONES|SE LEVANTA LA SESI[OÓ]N)", re.I)
# Cita combinada: "S-252 y 308/26" o "S-252, 308 y 310/26"
RE_EXP_COMBINADA = re.compile(r"\b([A-ZÑ.]{1,5})-(\d+(?:\s*(?:,|y)\s*(?:[A-ZÑ.]{1,5}-)?\d+)+)/(\d{2})\b")


def seccion_desde_titulo(titulo):
    t = titulo.upper()
    if t.startswith("PROYECTOS DE LEY"):
        return "ley"
    if t.startswith("PROYECTOS DE DECRETO"):
        return "decreto_res_com_dec"
    if t.startswith("ACUERDOS CONSIDERADOS") or t.startswith("ACUERDOS"):
        return "acuerdo"
    if t.startswith("MOCIONES DE PREFERENCIA"):
        return "preferencia"
    return None  # lista de asuntos, diarios, privilegio, etc. -> se ignoran


def expedientes_texto(texto):
    """Como extraer_expedientes pero entiende citas combinadas tipo
    'S-252 y 308/26' (dos números que comparten el '/año')."""
    encontrados = []
    for m in RE_EXP_COMBINADA.finditer(texto or ""):
        origen = m.group(1).replace(".", "")
        for n in re.findall(r"\d+", m.group(2)):
            encontrados.append(f"{origen}-{n}/{m.group(3)}")
    simples = extraer_expedientes(RE_EXP_COMBINADA.sub(" ", texto or ""))
    for e in simples:
        if e not in encontrados:
            encontrados.append(e)
    return encontrados


def separar_resultado(linea):
    """'APROBADO con modificaciones - Vuelve a la H. Cámara.' ->
    ('APROBADO con modificaciones', 'Vuelve a la H. Cámara.')"""
    partes = re.split(r"\s*[-–—]\s+", linea, maxsplit=1)
    res = norm_celda(partes[0]).rstrip(".")
    obs = norm_celda(partes[1]) if len(partes) > 1 else ""
    # "APROBADO S/T." (sin texto / sin orden del día) -> resultado "APROBADO"
    res = re.sub(r"\s+S/T$", "", res, flags=re.I)
    return res, obs


def parsear_boletin_texto(pdf_bytes, nro_boletin, fecha_sesion):
    items = []
    errores = []
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            lineas = []
            for pagina in pdf.pages:
                txt = pagina.extract_text() or ""
                lineas.extend(norm_celda(l) for l in txt.splitlines())
    except Exception as e:
        return [], [f"texto: apertura/lectura del PDF falló: {e}"]

    seccion = None
    entrada = None  # {"od": int|None, "texto": str}

    def cerrar(resultado, obs):
        nonlocal entrada
        if entrada is None:
            return
        texto = entrada["texto"]
        if seccion == "preferencia":
            if resultado.upper().startswith("APROBADA"):
                m = RE_SOLICITANTE.match(texto)
                solicitante = norm_celda(m.group(1)) if m else None
                for exp in expedientes_texto(texto):
                    it = {"expediente": exp, "od_nro": None, "resultado": "APROBADA",
                          "observaciones": obs, "seccion": seccion,
                          "fecha_sesion": fecha_sesion, "nro_boletin": nro_boletin}
                    if solicitante:
                        it["solicitante"] = solicitante
                    items.append(it)
        else:
            for exp in expedientes_texto(texto):
                items.append({"expediente": exp, "od_nro": entrada["od"],
                              "resultado": resultado, "observaciones": obs,
                              "seccion": seccion, "fecha_sesion": fecha_sesion,
                              "nro_boletin": nro_boletin})
        entrada = None

    for linea in lineas:
        if not linea or RE_PIE_TXT.match(linea):
            continue
        m = RE_SECCION_TXT.match(linea)
        if m and m.group(1).upper() == m.group(1):  # título en mayúsculas
            entrada = None
            seccion = seccion_desde_titulo(m.group(1))
            continue
        if seccion is None:
            continue
        if entrada is not None and RE_RESULTADO_TXT.match(linea):
            res, obs = separar_resultado(linea)
            cerrar(res, obs)
            continue
        mo = RE_ENTRADA_OD.match(linea)
        ms = RE_ENTRADA_ST.match(linea)
        if mo:
            entrada = {"od": int(mo.group(1)), "texto": mo.group(2)}
        elif ms:
            entrada = {"od": None, "texto": ms.group(1)}
        elif entrada is not None:
            entrada["texto"] += " " + linea
        elif seccion == "preferencia" and (RE_SOLICITANTE.match(linea) or RE_EXP_INICIO.match(linea)):
            # "Apellido: S-123/26, ..." o, sin apellido, "S-123/26, proyecto de ..."
            entrada = {"od": None, "texto": linea}
        elif seccion == "decreto_res_com_dec" and not linea.endswith(":"):
            # "Varios señores senadores: Proyecto de resolución que ... (S-1911/26)" + "APROBADO S/T."
            entrada = {"od": None, "texto": linea}
        # líneas sueltas ("Comisiones de X y de Y:") se ignoran
    if entrada is not None:
        errores.append("texto: una entrada quedó sin resultado y se descartó")
    return items, errores


def descargar_boletin(url):
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.content


def main():
    log.info("=" * 60)
    log.info("scraper_sanciones iniciado" + (" (TEST)" if TEST else ""))

    # El endpoint a veces devuelve una página de rechazo del sitio (no JSON)
    # en vez de los datos — probablemente rate-limit/anti-bot intermitente.
    # Vale la pena reintentar con espera antes de darse por vencido.
    boletines = []
    for intento in range(1, 4):
        try:
            boletines = obtener_listado_boletines()
            break
        except Exception as e:
            log.error(f"ERROR al obtener listado de boletines (intento {intento}/3): {e}")
            if intento < 3:
                log.warning("  reintentando en 20s...")
                time.sleep(20)
    else:
        return
    log.info(f"  -> {len(boletines)} boletines disponibles (anio >= {MIN_ANIO})")

    procesados = cargar_procesados()
    # SANCIONES_REPROCESAR="8/26,9/26": vuelve a leer esos boletines (quita sus ítems anteriores
    # y los marca como no procesados). Sirve cuando se corrige el lector.
    # SANCIONES_REPROCESAR="TODOS" relee todos los boletines del listado.
    pedido = os.getenv("SANCIONES_REPROCESAR", "").strip()
    if pedido.upper() == "TODOS":
        reprocesar = {b["nro_boletin"] for b in boletines}
    else:
        reprocesar = {x.strip() for x in pedido.split(",") if x.strip()}
    previas_por_boletin = {}
    if reprocesar and not TEST:
        previas = cargar_sanciones()
        for it in previas:
            if it.get("nro_boletin") in reprocesar:
                previas_por_boletin.setdefault(it["nro_boletin"], []).append(it)
        quedan = [it for it in previas if it.get("nro_boletin") not in reprocesar]
        log.info(f"  -> reprocesando {len(reprocesar)} boletines: se descartan {len(previas) - len(quedan)} ítems previos")
        guardar_sanciones(quedan)
        procesados -= reprocesar
    pendientes = [b for b in boletines if b["nro_boletin"] not in procesados]
    log.info(f"  -> {len(pendientes)} boletines pendientes de procesar")

    if TEST:
        pendientes = pendientes[:1]

    sanciones = cargar_sanciones()
    total_nuevos = {"ley": 0, "decreto_res_com_dec": 0, "acuerdo": 0, "preferencia": 0}

    for b in pendientes:
        nro_boletin = b["nro_boletin"]
        log.info(f"  Procesando boletín {nro_boletin} ({b['fecha_sesion']})...")
        try:
            pdf_bytes = descargar_boletin(b["url"])
        except Exception as e:
            log.error(f"    ERROR al descargar {nro_boletin}: {e}")
            continue

        items, errores = parsear_boletin(pdf_bytes, nro_boletin, b["fecha_sesion"])
        for err in errores:
            log.warning(f"    [{nro_boletin}] {err}")

        for it in items:
            total_nuevos[it["seccion"]] = total_nuevos.get(it["seccion"], 0) + 1
        log.info(f"    -> {len(items)} items extraidos")
        if nro_boletin in previas_por_boletin:
            # Comparación con lo que había cargado antes (por ejemplo, a mano): qué se suma y qué se pierde.
            antes = {(i["expediente"], i["seccion"]) for i in previas_por_boletin[nro_boletin]}
            ahora = {(i["expediente"], i["seccion"]) for i in items}
            log.info(f"    [comparación {nro_boletin}] antes {len(antes)} | ahora {len(ahora)} | "
                     f"se suman {len(ahora - antes)} | se pierden {len(antes - ahora)}")
            if antes - ahora:
                log.warning(f"      SE PIERDEN: {sorted(antes - ahora)[:20]}")
            if ahora - antes:
                log.info(f"      SE SUMAN: {sorted(ahora - antes)[:20]}")

        if TEST:
            print(json.dumps(items, ensure_ascii=False, indent=2))
        else:
            sanciones.extend(items)
            procesados.add(nro_boletin)

        time.sleep(PAUSA_ENTRE_REQUESTS)

    if TEST:
        log.info("TEST: no se escribió data/sanciones.json ni sanciones_procesados.json")
        return

    guardar_sanciones(sanciones)
    guardar_procesados(procesados)
    log.info(f"  -> nuevos por seccion: {total_nuevos}")
    log.info(f"  -> TOTAL en sanciones.json: {len(sanciones)}")
    log.info("scraper_sanciones finalizado.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()