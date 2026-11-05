#!/usr/bin/env python3
"""
scraper_proyectos.py — Proyectos ingresados en el Senado → data/proyectos.json
==============================================================================
Adaptado de scraper_senado.py (repo Proyectos-ingresados). Cambios:
  - Salida a data/proyectos.json (no TSV).
  - Lee data/proyectos.json existente: solo procesa expedientes nuevos.
  - Padrón de senadores desde data/senadores.json (construir_senadores.py), con
    fallback a scraping web si el JSON no existe.
  - Modo migración (MIGRAR_TSV): siembra proyectos.json desde un trazabilidad.tsv.
  - Mantiene la lógica de cruce autores→bloques/provincias y el filtro de
    sancionados/archivados.

Variables de entorno opcionales:
    MIGRAR_TSV       Ruta a un trazabilidad.tsv para sembrar la base (one-shot).
    SCRAPE           "0" para saltar el scraping web (solo migración). Default "1".
    FECHA_DESDE      Fecha de inicio fija DD/MM/YYYY (ignora VENTANA_DIAS).
    VENTANA_DIAS     Días hacia atrás para el scraping (default 30).
"""

import csv
import io
import json
import logging
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from autoria_caratula import calcular_autoria  # noqa: E402

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: faltan dependencias. Ejecutá: pip install -r requirements.txt")
    sys.exit(1)

try:
    import pdfplumber
    _PDFPLUMBER_OK = True
except ImportError:
    _PDFPLUMBER_OK = False

# ─────────────────────────────── Configuración ────────────────────────────────

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
PROYECTOS_JSON = os.path.join(DATA_DIR, "proyectos.json")
SENADORES_JSON = os.path.join(DATA_DIR, "senadores.json")
ACUERDOS_JSON = os.path.join(DATA_DIR, "acuerdos.json")

MIGRAR_TSV = os.getenv("MIGRAR_TSV", "")
SCRAPE = os.getenv("SCRAPE", "1") != "0"
FECHA_DESDE_FIJA = os.getenv("FECHA_DESDE", "")
VENTANA_DIAS = int(os.getenv("VENTANA_DIAS", "30"))

BASE_URL = "https://www.senado.gob.ar"
URL_BUSQUEDA = f"{BASE_URL}/parlamentario/parlamentaria/"
URL_FECHA_MESA = f"{BASE_URL}/parlamentario/parlamentaria/fechaMesa"

# Lista oficial completa (19 tipos), confirmada por Mariano — hasta la migración de
# 2026-08 sólo se incluía un subconjunto de 7.
TIPOS = {
    "AC": "Acuerdo",
    "CA": "Comunicación de Auditoría",
    "CC": "Comunicación de Comisiones",
    "CD": "Comunicación de Diputados",
    "CE": "Comunicación del Poder Ejecutivo",
    "CM": "Comunicación de Ministerios",
    "CO": "Comunicación de Senadores",
    "CV": "Comunicación Varia",
    "DC": "Decreto",
    "MS": "Mensaje de Senado",
    "MD": "Mensaje de Diputados",
    "PP": "Petición",
    "PC": "Proyecto de Comunicación",
    "PD": "Proyecto de Declaración",
    "DE": "Proyecto de Decreto",
    "PL": "Proyecto de Ley",
    "PR": "Proyecto de Resolución",
    "RC": "Resolución Conjunta",
    "RP": "Respuesta de Presidencia",
}
TIPOS_INCLUIR = frozenset(TIPOS.keys())

# Cuántos expedientes "abiertos" (no archivados/sancionados/dados cuenta) se
# re-visitan por corrida para actualizar trazabilidad — ver revisar_expedientes_abiertos().
LOTE_REVISION = int(os.getenv("LOTE_REVISION", "200"))

PAUSA_ENTRE_REQUESTS = 1.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ─────────────────────────────── Padrón senadores ────────────────────────────

def _sin_tildes(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def cargar_padron():
    """Devuelve (padron, indice_apellido). Usa data/senadores.json; si no existe,
    lo construye desde los xlsx via construir_senadores."""
    padron = {}
    if os.path.exists(SENADORES_JSON):
        with open(SENADORES_JSON, "r", encoding="utf-8") as f:
            padron = json.load(f)
    else:
        try:
            from construir_senadores import construir_padron
            padron = construir_padron()
            log.info("senadores.json no existe; padrón construido desde xlsx en memoria")
        except Exception as exc:
            log.warning(f"No se pudo construir el padrón: {exc}")
    indice = {}
    for nombre_norm, info in padron.items():
        apellido = nombre_norm.split(",")[0].strip()
        indice.setdefault(_sin_tildes(apellido).upper(), info)
    log.info(f"  → padrón con {len(padron)} senadores")
    return padron, indice


# ─────────────────────────────── Helpers ─────────────────────────────────────

def normalizar_autor(nombre_sitio):
    if not nombre_sitio:
        return ""
    if "," not in nombre_sitio:
        return nombre_sitio.strip().upper()
    apellido, nombre = nombre_sitio.split(",", 1)
    return f"{apellido.strip()}, {nombre.strip()}".upper()


def buscar_info(nombre_norm, padron, indice_apellido):
    if nombre_norm in padron:
        return padron[nombre_norm]
    apellido = nombre_norm.split(",")[0].strip() if "," in nombre_norm else nombre_norm.strip()
    clave = _sin_tildes(apellido).upper()
    if clave in indice_apellido:
        return indice_apellido[clave]
    return {"bloque": "Sin datos", "provincia": ""}


def get_bloques(autores, padron, indice):
    seen, result = set(), []
    for autor in autores:
        bloque = buscar_info(autor, padron, indice).get("bloque", "Sin datos")
        if bloque and bloque not in seen:
            seen.add(bloque)
            result.append(bloque)
    return result


def get_provincias(autores, padron, indice):
    seen, result = set(), []
    for autor in autores:
        prov = buscar_info(autor, padron, indice).get("provincia", "")
        if prov and prov not in seen:
            seen.add(prov)
            result.append(prov)
    return result


def clasificar_autores(extracto, autores_detalle):
    """Separa autores principales de coautores según 'Y OTROS' en el extracto."""
    if not autores_detalle:
        return [], []
    atrib = extracto.split(":")[0].upper() if ":" in extracto else extracto.upper()
    tiene_y_otros = bool(re.search(r'\bY\s+OTR[OA]S?\b', atrib))
    if not tiene_y_otros:
        return autores_detalle, []
    atrib_limpio = re.sub(r'\s*\bY\s+OTR[OA]S?\b', '', atrib).strip()
    partes = re.split(r'[,]\s*|\s+Y\s+', atrib_limpio)
    apellidos_extracto = [p.strip() for p in partes if p.strip()]
    autores, coautores = [], []
    for autor in autores_detalle:
        apellido = autor.split(",")[0].strip().upper()
        es_principal = any(ap in apellido or apellido in ap for ap in apellidos_extracto)
        (autores if es_principal else coautores).append(autor)
    if not autores and autores_detalle:
        autores = [autores_detalle[0]]
        coautores = autores_detalle[1:]
    return autores, coautores


def construir_url_expediente(nro, anio, origen, tipo):
    anio_short = str(anio)[-2:]
    return f"{BASE_URL}/parlamentario/comisiones/verExp/{nro}.{anio_short}/{origen}/{tipo}"


def clave_proyecto(p):
    """Clave de deduplicación. Incluye el ORIGEN: la numeración es independiente por origen
    (S, PE, CD, OV, P), así que S-94/26 y PE-94/26 son expedientes distintos aunque
    compartan número, año y tipo. Sin el origen, el segundo en llegar se descartaba en
    silencio (así se perdieron 21 proyectos de ley de 2026 y 15 de 2025)."""
    return (int(p["nro"]), int(p["anio"]), str(p["tipo"]).strip(), str(p.get("origen") or "").strip())


# ─────────────────────────────── Persistencia JSON ───────────────────────────

def cargar_proyectos_existentes():
    if not os.path.exists(PROYECTOS_JSON):
        return [], set()
    with open(PROYECTOS_JSON, "r", encoding="utf-8") as f:
        proyectos = json.load(f)
    claves = {clave_proyecto(p) for p in proyectos}
    return proyectos, claves


def guardar_proyectos(proyectos):
    os.makedirs(DATA_DIR, exist_ok=True)
    # Orden: año desc, nro desc
    proyectos.sort(key=lambda p: (int(p["anio"]), int(p["nro"])), reverse=True)
    with open(PROYECTOS_JSON, "w", encoding="utf-8") as f:
        json.dump(proyectos, f, ensure_ascii=False, indent=2)


# ─────────────────────────────── acuerdos.json (dado cuenta) ─────────────────

def cargar_acuerdos():
    if not os.path.exists(ACUERDOS_JSON):
        return []
    with open(ACUERDOS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_acuerdos(acuerdos):
    os.makedirs(DATA_DIR, exist_ok=True)
    acuerdos.sort(key=lambda a: (int(a["anio"]), int(a["nro"])), reverse=True)
    with open(ACUERDOS_JSON, "w", encoding="utf-8") as f:
        json.dump(acuerdos, f, ensure_ascii=False, indent=2)


def actualizar_acuerdo(acuerdos_por_clave, proyecto, detalle):
    """Crea/actualiza la entrada de data/acuerdos.json para un expediente AC con
    lo que se pudo leer en vivo (dado_cuenta/dae). No toca aprobado/fecha_aprobacion/
    nro_od si la entrada ya existía — esos siguen viniendo del cruce con od.json/
    sanciones.json en generar_web.py."""
    clave = (proyecto["nro"], proyecto["anio"])
    dae_num = None
    if detalle.get("dae"):
        try:
            dae_num = int(detalle["dae"].split("/")[0])
        except ValueError:
            dae_num = None
    existente = acuerdos_por_clave.get(clave)
    if existente is None:
        existente = {
            "nro": proyecto["nro"], "anio": proyecto["anio"],
            "caratula": proyecto["extracto"], "origen": proyecto["origen"],
            "dae": dae_num, "dado_cuenta": False, "fecha_dado_cuenta": None,
            "aprobado": False, "fecha_aprobacion": None, "nro_od": None,
        }
        acuerdos_por_clave[clave] = existente
    if dae_num is not None:
        existente["dae"] = dae_num
    if detalle.get("dado_cuenta") is not None:
        existente["dado_cuenta"] = detalle["dado_cuenta"]
        existente["fecha_dado_cuenta"] = detalle["fecha_dado_cuenta"]


# ─────────────────────────────── Migración TSV ───────────────────────────────

def migrar_desde_tsv(tsv_path, padron, indice, claves_existentes):
    """Convierte filas del TSV a dicts de proyecto (formato proyectos.json).
    Solo devuelve los que no estén ya en claves_existentes."""
    if not os.path.exists(tsv_path):
        log.warning(f"  TSV no encontrado: {tsv_path}")
        return []
    nuevos = []
    with open(tsv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            nro_str = (row.get("NRO") or "").strip()
            if not nro_str:
                continue
            nro = int(nro_str)
            anio = int((row.get("ANIO") or "2025").strip() or "2025")
            tipo = (row.get("TIPO") or "PL").strip()
            origen = (row.get("ORIGEN") or "S").strip()
            if (nro, anio, tipo, origen) in claves_existentes:
                continue

            caratula = (row.get("CARATULA") or "").strip()
            extracto = caratula[caratula.index(":") + 1:].strip() if ":" in caratula else caratula

            mesa_raw = (row.get("MESA") or "").strip()
            fecha = ""
            fm = re.search(r"(\d{2}/\d{2}/\d{4})", mesa_raw)
            if fm:
                fecha = fm.group(1)

            dae_raw = (row.get("DAE") or "").strip()
            dae = ""
            md = re.match(r"(\d+)", dae_raw)
            if md:
                ma = re.search(r"(\d{4})", dae_raw)
                if ma:
                    dae = f"{md.group(1)}/{ma.group(1)}"

            autor_raw = (row.get("AUTOR") or "").strip()
            todos = []
            if autor_raw:
                for a in autor_raw.split(" - "):
                    a = a.strip().rstrip("-").strip()
                    if a:
                        todos.append(normalizar_autor(a))

            autores, coautores = clasificar_autores(caratula, todos)
            autores_car, bloques_car, _ = calcular_autoria(caratula, todos, padron)
            comisiones = [(row.get(f"COM{i}") or "").strip()
                          for i in range(1, 6) if (row.get(f"COM{i}") or "").strip()]

            nuevos.append({
                "nro": nro,
                "anio": anio,
                "tipo": tipo,
                "tipo_label": TIPOS.get(tipo, tipo),
                "extracto": extracto,
                "autores": autores,
                "coautores": coautores,
                "bloques": get_bloques(autores, padron, indice),
                "provincias": get_provincias(autores, padron, indice),
                "comisiones": comisiones,
                "fecha": fecha,
                "dae": dae,
                "origen": origen,
                "url": construir_url_expediente(nro, anio, origen, tipo),
                "sancionado": False,
                "ley_numero": None,
                "fecha_ley": None,
                "archivado": False,
                "fecha_archivo": None,
                "caduca": False,
                "fecha_caduca": None,
                **({"autores_caratula": autores_car, "bloques_caratula": bloques_car} if autores_car else {}),
            })
            claves_existentes.add((nro, anio, tipo, origen))
    log.info(f"  → migración: {len(nuevos)} proyectos nuevos desde TSV")
    return nuevos


# ─────────────────────────────── Scraping web ────────────────────────────────

def obtener_token(session):
    resp = session.get(URL_BUSQUEDA, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    inp = soup.find("input", {"name": "busqueda_proyectos[_token]"})
    if not inp:
        raise RuntimeError("No se encontró busqueda_proyectos[_token]")
    return inp["value"]


def parsear_tabla_resultados(html):
    soup = BeautifulSoup(html, "html.parser")
    tablas = soup.find_all("table")
    if not tablas:
        return []
    tabla = max(tablas, key=lambda t: len(t.find_all("tr")))
    filas = []
    for tr in tabla.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 6:
            continue
        link = tds[0].find("a", href=True)
        if not link:
            continue
        exp_text = tds[0].get_text(strip=True)
        url = link["href"]
        if url and not url.startswith("http"):
            url = BASE_URL + url
        tipo = tds[1].get_text(strip=True)
        origen = tds[2].get_text(strip=True)
        fecha = tds[4].get_text(strip=True)
        caratula = tds[5].get_text(strip=True)
        if tipo not in TIPOS_INCLUIR:
            continue
        m = re.match(r"(\d+)/(\d+)", exp_text)
        if not m:
            continue
        nro = int(m.group(1))
        anio_str = m.group(2)
        anio = int("20" + anio_str) if len(anio_str) == 2 else int(anio_str)
        extracto = caratula[caratula.index(":") + 1:].strip() if ":" in caratula else caratula
        filas.append({
            "nro": nro, "anio": anio, "tipo": tipo, "origen": origen,
            "fecha": fecha, "extracto": extracto, "url": url, "caratula": caratula,
        })
    return filas


def buscar_por_fechas(session, fecha_desde, fecha_hasta):
    token = obtener_token(session)
    payload = {
        "busqueda_proyectos[fechaDesdeMesa][day]": str(fecha_desde.day),
        "busqueda_proyectos[fechaDesdeMesa][month]": str(fecha_desde.month),
        "busqueda_proyectos[fechaDesdeMesa][year]": str(fecha_desde.year),
        "busqueda_proyectos[fechaHastaMesa][day]": str(fecha_hasta.day),
        "busqueda_proyectos[fechaHastaMesa][month]": str(fecha_hasta.month),
        "busqueda_proyectos[fechaHastaMesa][year]": str(fecha_hasta.year),
        "busqueda_proyectos[_token]": token,
    }
    log.info(f"POST {URL_FECHA_MESA} | {fecha_desde:%d/%m/%Y} → {fecha_hasta:%d/%m/%Y}")
    resp = session.post(URL_FECHA_MESA, data=payload, timeout=30)
    resp.raise_for_status()
    todos, pagina, html = [], 1, resp.text
    while True:
        filas = parsear_tabla_resultados(html)
        log.info(f"  Página {pagina}: {len(filas)} expedientes de interés")
        todos.extend(filas)
        soup = BeautifulSoup(html, "html.parser")
        next_link = soup.find("a", href=re.compile(rf"[?&]page={pagina + 1}"))
        if not next_link:
            break
        pagina += 1
        url_sig = next_link["href"]
        if not url_sig.startswith("http"):
            url_sig = BASE_URL + url_sig
        time.sleep(PAUSA_ENTRE_REQUESTS)
        resp = session.get(url_sig, timeout=30)
        resp.raise_for_status()
        html = resp.text
    log.info(f"  → {len(todos)} expedientes en total")
    return todos


def _fecha_guiones_a_barras(texto):
    """'24-06-2026' -> '24/06/2026'. None si no matchea o es 'SIN FECHA'."""
    if not texto:
        return None
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", texto)
    return f"{m.group(1)}/{m.group(2)}/{m.group(3)}" if m else None


def _tabla_por_resumen(soup, resumen_contiene):
    for tabla in soup.find_all("table"):
        resumen = (tabla.get("summary") or "").upper()
        if resumen_contiene in resumen:
            return tabla
    return None


def _parsear_comisiones(soup):
    """Tabla 'Giros del Expediente a Comisiones': sólo nos interesa el nombre de
    la comisión de cada giro (en orden); no se guardan fechas de ingreso/egreso."""
    comisiones = []
    tabla = _tabla_por_resumen(soup, "GIROS DEL EXPEDIENTE")
    if not tabla:
        return comisiones
    for tr in tabla.select("tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 1:
            continue
        com = re.sub(r"ORDEN DE GIRO:.*$", "", tds[0].get_text(" ", strip=True), flags=re.S).strip()
        if com:
            comisiones.append(com)
    return comisiones


def _parsear_sancion_de_ley(soup):
    """Tabla summary='SANCION DE LEY': filas 'FECHA DE SANCION: dd-mm-aaaa' /
    'NUMERO DE LEY: NNNNN'. Sólo existe si el expediente se convirtió en ley."""
    tabla = _tabla_por_resumen(soup, "SANCION DE LEY")
    if not tabla:
        return None, None
    texto = tabla.get_text(" ", strip=True)
    fm = re.search(r"FECHA DE SANCION:\s*(\d{2}-\d{2}-\d{4})", texto)
    nm = re.search(r"NUMERO DE LEY:\s*(\d+)", texto)
    if not nm:
        return None, None
    return nm.group(1), (_fecha_guiones_a_barras(fm.group(1)) if fm else None)


def _parsear_dado_cuenta(soup):
    """Tabla 'Fechas en Mesa de Entradas' (sólo expedientes de Acuerdos): columna
    'DADO CUENTA' — 'SIN FECHA' si todavía no se dio cuenta."""
    tabla = _tabla_por_resumen(soup, "FECHAS EN MESA DE ENTRADAS")
    if not tabla:
        return None, None
    encabezados = [th.get_text(strip=True).upper() for th in tabla.select("thead th")]
    if "DADO CUENTA" not in encabezados:
        return None, None
    idx = encabezados.index("DADO CUENTA")
    fila = tabla.select_one("tbody tr")
    if not fila:
        return None, None
    celdas = fila.find_all("td")
    if idx >= len(celdas):
        return None, None
    valor = celdas[idx].get_text(strip=True)
    fecha = _fecha_guiones_a_barras(valor)
    return bool(fecha), fecha


def obtener_detalle(session, url):
    resultado = {
        "autores_raw": [], "comisiones": [], "dae": "",
        "archivado": False, "fecha_archivo": None,
        "caduca": False, "fecha_caduca": None,
        "sancionado": False, "ley_numero": None, "fecha_ley": None,
        "dado_cuenta": None, "fecha_dado_cuenta": None,
    }
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for link in soup.select("a[href*='/senadores/senador/']"):
            nombre = link.get("title", "").strip() or link.get_text(strip=True)
            if nombre:
                resultado["autores_raw"].append(nombre)

        resultado["comisiones"] = _parsear_comisiones(soup)

        texto = soup.get_text()
        dm = re.search(r"D\.A\.E\.\s*(\d+/\d{4})", texto) or re.search(r"(\d+/\d{4})\s*Tipo:", texto)
        if dm:
            resultado["dae"] = dm.group(1)

        m_archivo = re.search(r"ENVIADO AL ARCHIVO\s*:\s*(\d{2}-\d{2}-\d{4})", texto, re.I)
        if m_archivo:
            resultado["archivado"] = True
            resultado["fecha_archivo"] = _fecha_guiones_a_barras(m_archivo.group(1))
        m_caduco = re.search(r"EL EXPEDIENTE CADUCO EL\s*(\d{2}-\d{2}-\d{4})", texto, re.I)
        if m_caduco:
            resultado["archivado"] = True
            resultado["caduca"] = True
            resultado["fecha_caduca"] = _fecha_guiones_a_barras(m_caduco.group(1))

        ley_numero, fecha_ley = _parsear_sancion_de_ley(soup)
        if ley_numero:
            resultado["sancionado"] = True
            resultado["ley_numero"] = ley_numero
            resultado["fecha_ley"] = fecha_ley

        dado_cuenta, fecha_dado_cuenta = _parsear_dado_cuenta(soup)
        if dado_cuenta is not None:
            resultado["dado_cuenta"] = dado_cuenta
            resultado["fecha_dado_cuenta"] = fecha_dado_cuenta
    except Exception as exc:
        log.warning(f"    Error en detalle {url}: {exc}")
    return resultado


def _hoy_iso():
    return datetime.now().strftime("%Y-%m-%d")


def scrape_incremental(session, padron, indice, claves_existentes, acuerdos_por_clave):
    hoy = datetime.now()
    if FECHA_DESDE_FIJA:
        try:
            fecha_desde = datetime.strptime(FECHA_DESDE_FIJA, "%d/%m/%Y")
        except ValueError:
            log.error(f"FECHA_DESDE inválido: '{FECHA_DESDE_FIJA}'")
            return []
    else:
        fecha_desde = hoy - timedelta(days=VENTANA_DIAS)

    try:
        expedientes = buscar_por_fechas(session, fecha_desde, hoy)
    except Exception as exc:
        log.error(f"Error en búsqueda principal: {exc}")
        return []

    # Solo procesar expedientes que no estén ya en la base
    pendientes = [e for e in expedientes
                  if (e["nro"], e["anio"], e["tipo"], e["origen"]) not in claves_existentes]
    log.info(f"  → {len(pendientes)}/{len(expedientes)} expedientes nuevos a procesar")

    nuevos = []
    for i, exp in enumerate(pendientes, 1):
        log.info(f"  [{i:>3}/{len(pendientes)}] {exp['tipo']} {exp['nro']}/{exp['anio']}")
        time.sleep(PAUSA_ENTRE_REQUESTS)
        detalle = obtener_detalle(session, exp["url"]) if exp["url"] else {}
        autores_norm = [normalizar_autor(a) for a in detalle.get("autores_raw", []) if a.strip()]
        caratula = exp.get("caratula", exp["extracto"])
        autores, coautores = clasificar_autores(caratula, autores_norm)
        autores_car, bloques_car, _ = calcular_autoria(caratula, autores_norm, padron)
        proyecto = {
            "nro": exp["nro"],
            "anio": exp["anio"],
            "tipo": exp["tipo"],
            "tipo_label": TIPOS.get(exp["tipo"], exp["tipo"]),
            "extracto": exp["extracto"],
            "autores": autores,
            "coautores": coautores,
            "bloques": get_bloques(autores, padron, indice),
            "provincias": get_provincias(autores, padron, indice),
            "comisiones": detalle.get("comisiones", []),
            "fecha": exp["fecha"],
            "dae": detalle.get("dae", ""),
            "origen": exp["origen"],
            "url": exp["url"],
            "sancionado": detalle.get("sancionado", False),
            "ley_numero": detalle.get("ley_numero"),
            "fecha_ley": detalle.get("fecha_ley"),
            "archivado": detalle.get("archivado", False),
            "fecha_archivo": detalle.get("fecha_archivo"),
            "caduca": detalle.get("caduca", False),
            "fecha_caduca": detalle.get("fecha_caduca"),
            "_ultima_revision": _hoy_iso(),
        }
        if autores_car:
            # Autoría por el prefijo de la carátula (ver autoria_caratula.py)
            proyecto["autores_caratula"] = autores_car
            proyecto["bloques_caratula"] = bloques_car
        nuevos.append(proyecto)
        if exp["tipo"] == "AC":
            actualizar_acuerdo(acuerdos_por_clave, proyecto, detalle)
    return nuevos


def revisar_expedientes_abiertos(session, proyectos, acuerdos_por_clave):
    """Re-visita un lote acotado de expedientes ya existentes que sigan
    'abiertos' para actualizar archivo/caducidad/sanción/dado-cuenta con el
    tiempo, sin tener que re-scrapear toda la base en cada corrida (~4000
    expedientes). Prioriza los menos revisados recientemente."""
    def esta_abierto(p):
        if p.get("archivado") or p.get("sancionado"):
            return False
        if p.get("tipo") == "AC":
            clave = (p["nro"], p["anio"])
            acuerdo = acuerdos_por_clave.get(clave)
            if acuerdo and acuerdo.get("dado_cuenta"):
                return False
        return True

    abiertos = [p for p in proyectos if esta_abierto(p) and p.get("url")]
    abiertos.sort(key=lambda p: p.get("_ultima_revision") or "0000-00-00")
    lote = abiertos[:LOTE_REVISION]
    if not lote:
        return 0
    log.info(f"  → revisando {len(lote)}/{len(abiertos)} expedientes abiertos "
              f"(trazabilidad: archivo/caducidad/sanción/dado cuenta)")

    actualizados = 0
    for i, p in enumerate(lote, 1):
        log.info(f"  [rev {i:>3}/{len(lote)}] {p['tipo']} {p['nro']}/{p['anio']}")
        time.sleep(PAUSA_ENTRE_REQUESTS)
        detalle = obtener_detalle(session, p["url"])
        p["_ultima_revision"] = _hoy_iso()
        cambio = False
        for campo in ("archivado", "fecha_archivo", "caduca", "fecha_caduca",
                      "sancionado", "ley_numero", "fecha_ley", "comisiones"):
            valor = detalle.get(campo)
            if campo == "comisiones":
                if valor:
                    p[campo] = valor
                continue
            if valor and p.get(campo) != valor:
                p[campo] = valor
                cambio = True
        if p["tipo"] == "AC":
            antes = dict(acuerdos_por_clave.get((p["nro"], p["anio"]), {}))
            actualizar_acuerdo(acuerdos_por_clave, p, detalle)
            if acuerdos_por_clave.get((p["nro"], p["anio"])) != antes:
                cambio = True
        if cambio:
            actualizados += 1
    log.info(f"  → {actualizados} expedientes con cambios de trazabilidad")
    return actualizados


# ─────────────────────────────── Chequeo de huecos ────────────────────────────

def chequear_huecos(proyectos, anios=None):
    """Registra en el log, por año, cuántos expedientes de origen S hay en proyectos.json
    frente al número más alto visto. La numeración de S es una sola secuencia por año
    (compartida entre tipos), así que `máx - cantidad` indica cuántos números no están
    cargados; algunos son normales (tipos que no se guardan), pero un salto repentino entre
    corridas avisa de que se está perdiendo algo. También lista los números faltantes
    dentro de los 200 más recientes. Sólo informa: no modifica nada."""
    anio_actual = datetime.now().year
    for anio in (anios or (anio_actual, anio_actual - 1)):
        nros = {int(p["nro"]) for p in proyectos if p.get("origen") == "S" and int(p["anio"]) == anio}
        if not nros:
            log.info(f"  [huecos] S/{anio}: sin expedientes")
            continue
        maximo = max(nros)
        recientes = [n for n in range(max(1, maximo - 199), maximo + 1) if n not in nros]
        log.info(f"  [huecos] S/{anio}: {len(nros)} expedientes, número más alto {maximo}, "
                 f"sin cargar {maximo - len(nros)}; faltan en los últimos 200: {recientes[:30]}"
                 f"{'...' if len(recientes) > 30 else ''}")


# ─────────────────────────────── Main ─────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("scraper_proyectos iniciado")

    padron, indice = cargar_padron()
    proyectos, claves = cargar_proyectos_existentes()
    log.info(f"  → {len(proyectos)} proyectos ya en data/proyectos.json")
    acuerdos = cargar_acuerdos()
    acuerdos_por_clave = {(a["nro"], a["anio"]): a for a in acuerdos}

    # 1. Migración desde TSV (opcional, one-shot)
    if MIGRAR_TSV:
        migrados = migrar_desde_tsv(MIGRAR_TSV, padron, indice, claves)
        proyectos.extend(migrados)

    # 2. Scraping incremental web + revisión de trazabilidad de abiertos
    if SCRAPE:
        session = requests.Session()
        # Ver nota en scraper_agenda.py: un User-Agent de navegador dispara el
        # anti-bots del sitio; uno propio y honesto pasa sin problema. NO
        # cambiarlo por uno de navegador "para disimular".
        session.headers.update({
            "User-Agent": "HSN-SistemaLegislativo/1.0 (+https://github.com/bonifaciomariano/hsn-sistema-legislativo)"
        })
        nuevos = scrape_incremental(session, padron, indice, claves, acuerdos_por_clave)
        proyectos.extend(nuevos)
        log.info(f"  → {len(nuevos)} proyectos nuevos del scraping")

        revisar_expedientes_abiertos(session, proyectos, acuerdos_por_clave)

    guardar_proyectos(proyectos)
    chequear_huecos(proyectos)
    guardar_acuerdos(list(acuerdos_por_clave.values()))
    con_bloque = sum(1 for p in proyectos if p["bloques"] and p["bloques"] != ["Sin datos"])
    log.info(f"  → TOTAL en proyectos.json: {len(proyectos)} ({con_bloque} con bloque)")
    log.info("scraper_proyectos finalizado.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
