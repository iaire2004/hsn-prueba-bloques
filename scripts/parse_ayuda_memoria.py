"""Migra AYUDA_MEMORIA_2026.xlsx (planilla manual, única fuente) a
data/ayuda_memoria.json.

Antes este script cruzaba ordenes_dia_2026.xlsx (export del sitio del
Senado) con AYUDA_MEMORIA_2026.xlsx para enriquecer con firmantes/comisión
cabecera. A pedido de Mariano (22/9/26) se pasó a usar sólo
AYUDA_MEMORIA_2026.xlsx: trae expedientes con hipervínculos reales,
firmantes y comisión cabecera en una sola planilla, y si un OD no está ahí
es porque ya se trató y no tiene que aparecer en la web.

Hojas leídas: "OD LEY", "ANEXO I" (OD de resolución/comunicación/
declaración pese al nombre de la hoja) y "OD ACUERDOS".

Cada fila trae en una sola celda "AUTORES Y CONTENIDO" tanto el autor como
la descripción, ya en buena mayúscula/minúscula (no como el viejo extracto
del sitio del Senado, que venía todo en mayúsculas). El autor se extrae con
una regex sobre "señor/a senador/a <Nombre>" — no es infalible (ver aviso
al final de la corrida para los casos que quedan sin autor detectado más
allá de los esperados: mensajes del PEN, proyectos venidos en revisión de
Diputados, notas de particulares y "varios señores/as senadores/as").

Un OD "N y ANEXO" (dictamen de mayoría + dictamen de minoría adjunto) se
desdobla en dos filas de salida: tipoOD NORMAL con los firmantes de
mayoría y tipoOD ANEXO con los firmantes de minoría (el texto que sigue a
"ANEXO:" en la columna de firmantes) — mismo expediente y descripción.
Si la planilla no trae "ANEXO:" (no cargaron los firmantes de minoría)
pero el anexo existe igual, hay que agregarlo a mano en
OVERRIDES_MINORIA_SIN_FIRMANTES (link de descarga provisto por Mariano,
sin firmantes porque la planilla no los tiene).

La planilla no trae fecha de dictamen ni la lista completa de comisiones de
giro (sólo la cabecera). Eso se completa cruzando con
ordenes_dia_oficial_2026.xlsx, el export "Órdenes del Día" del sitio del
Senado (columnas Giros y Fecha Dictamen), por (número, período, tipo de OD).
La planilla sigue siendo la única que decide QUÉ OD aparecen; el export sólo
enriquece las que ya están. Se llama distinto de ordenes_dia_2026.xlsx a
propósito: ése lo regenera solo generar_ordenes_dia_xlsx.py desde od.json
(sin fechas) y pisaría el oficial. Si una OD nueva de la planilla no está en
el export, queda sin fecha y con la cabecera como única comisión: hay que
volver a bajar el export.

Ejecutar con: py scripts/parse_ayuda_memoria.py
"""
import json
import os
import re
from datetime import datetime

import openpyxl

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AYUDA_MEMORIA_PATH = os.path.join(BASE, "AYUDA_MEMORIA_2026.xlsx")
JSON_PATH = os.path.join(BASE, "data", "ayuda_memoria.json")
ORDENES_DIA_OFICIAL_PATH = os.path.join(BASE, "ordenes_dia_oficial_2026.xlsx")

ORIGEN_MAP = {"PE": "Poder Ejecutivo", "S": "Senado", "CD": "Cámara de Diputados"}
CATEGORIA_MAP = {
    "PL": "Proyecto de Ley",
    "PD": "Proyecto de Declaración",
    "PC": "Proyecto de Comunicación",
    "PR": "Proyecto de Resolución",
    "AC": "Acuerdo",
}

HOJAS = ["OD LEY", "ANEXO I", "OD ACUERDOS"]

# (numero, periodo) -> odLink del anexo en minoría, para OD "N y ANEXO" cuya
# planilla no trae "ANEXO:" con los firmantes (el anexo existe en el sitio
# del Senado igual, sólo que no se cargaron los firmantes a mano).
OVERRIDES_MINORIA_SIN_FIRMANTES = {
    (135, 2026): "https://www.senado.gob.ar/parlamentario/parlamentaria/51664/downloadOrdenDia",
}

# (numero, periodo) -> autor correcto, para los casos en que RE_AUTOR no
# reconoce a todos los firmantes por un typo en el texto de la planilla
# (ej. "señora senado Huala" en vez de "señora senadora Huala").
OVERRIDES_AUTOR = {
    (138, 2026): "de Pedro y Huala",
}

# OD que todavía no están en la planilla ni en el export oficial y se cargan a
# mano desde el PDF de la OD (a pedido de Mariano). Cuando aparezcan en la
# planilla, borrar la entrada de acá. odLink None: el ID del sitio no se conoce.
OD_MANUALES = [
    {
        "numero": "408",
        "periodo": 2026,
        "origen": "Poder Ejecutivo",
        "categoria": "Proyecto de Ley",
        "autor": None,
        "descripcion": "Dictamen aceptando las modificaciones introducidas por la Honorable Cámara de Diputados al Tratado de Cooperación en materia de Patentes (PCT) y su reglamento. (PE-854/97)",
        "expedientes": [{
            "codigo": "PE-854/97",
            "url": "https://www.senado.gob.ar/parlamentario/comisiones/verExp/854.97/PE/PL",
        }],
        "comisionCabecera": "Relaciones Exteriores y Culto",
        "comisiones": ["Relaciones Exteriores y Culto", "Industria y Comercio"],
        "fechaDictamen": "15/10/2026",
        "odLink": None,
        "tipoOD": "NORMAL",
        "firmantesTxt": (
            "Francisco M. Paoltroni – Romina M. Almeida – Ivanna M. Arrascaeta – "
            "Joaquín A. Benegas Lynch – Agustín A. Monteverde – Mario P. Cervi – "
            "Gonzalo Guzmán Coraita – Agustín P. Coto – María B. Monte de Oca – "
            "Carlos M. Espínola – Sonia E. Rojas Decut – Silvana L. Schneider – "
            "Eduardo A. Vischi – Mercedes G. Valenzuela – Carolina Losada – "
            "Maximiliano Abad – Rodolfo A. Suárez – Enrique M. Goerling Lara. "
            "En disidencia: Guillermo E. Andrada – Sandra M. Mendoza."
        ),
    },
]

RE_URL_ORIGEN_TIPO = re.compile(r"/([A-Z]+)/([A-Z]+)$")
RE_AUTOR = re.compile(
    r"se\w*or\w*\s+senador\w*\s+"
    r"(.+?)(?=,| y (?:en |el |la |los |las |del |de la |de los |de las )"
    r"| que | por el que |\(|\.|$)",
    re.IGNORECASE | re.UNICODE,
)


def _parsear_od_numero(valor):
    """'223/26 ' -> (223, 2026, 'NORMAL'); '113/2026 y ANEXO' -> (113, 2026, 'NORMAL',
    con y_anexo=True)."""
    if isinstance(valor, datetime):
        return valor.month, valor.year, False
    s = str(valor or "").strip()
    y_anexo = "y anexo" in s.lower()
    s = re.sub(r"\s+y\s+anexo.*$", "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"\s*\([AN]\)\s*", "", s, flags=re.IGNORECASE).strip()
    m = re.match(r"^(\d+)\s*/\s*(\d+)$", s)
    if not m:
        return None, None, False
    nro = int(m.group(1))
    anio = int(m.group(2))
    if anio < 100:
        anio += 2000
    return nro, anio, y_anexo


RE_SPLIT_FIRMANTES = re.compile(
    r"\s+–\s+|\s+-\s+|\.\s*en\s+disidencia(?:\s+parcial)?:\s*", re.IGNORECASE
)


def _parsear_firmantes(texto):
    """Separa firmantes por guion/raya. Los que firmaron 'en disidencia
    (parcial)' vienen con un '. En disidencia: <nombre>' pegado en vez de
    guion — se corta ahí también y se pierde la nota de disidencia (queda
    sólo como firmante más, no se distingue de los demás)."""
    if not texto:
        return []
    partes = RE_SPLIT_FIRMANTES.split(re.sub(r"\s+", " ", texto.strip()))
    out = []
    for p in partes:
        p = p.strip().rstrip(".").strip()
        if p:
            out.append(p)
    return out


def _extraer_autor(texto):
    matches = RE_AUTOR.findall(texto or "")
    if not matches:
        return None
    return " y ".join(m.strip().rstrip(".") for m in matches)


def _origen_y_categoria(url):
    """Del link de expediente (.../verExp/351.26/S/PL) saca origen y
    categoría; son más confiables que parsear el código a mano porque la
    celda EXPTE. N° no siempre trae el sufijo de tipo."""
    if not url:
        return "", "Proyecto de Ley"
    m = RE_URL_ORIGEN_TIPO.search(url)
    if not m:
        return "", "Proyecto de Ley"
    origen = ORIGEN_MAP.get(m.group(1), m.group(1).title())
    categoria = CATEGORIA_MAP.get(m.group(2), "Proyecto de Ley")
    return origen, categoria


def _parsear_expedientes(exp_raw, primer_url):
    if not exp_raw or not exp_raw.strip():
        return []
    codigos = []
    for segmento in re.split(r"[\n]", exp_raw.strip()):
        for sub in re.split(r"\s+-\s+", segmento.strip()):
            sub = re.sub(r"-\s+", "-", sub.strip()).strip(", ").strip()
            if not sub:
                continue
            m = re.match(r"^([A-Z]+)-(.+)$", sub)
            if not m:
                codigos.append(sub)
                continue
            prefijo, resto = m.group(1), m.group(2)
            partes = [p.strip() for p in re.split(r",|\sy\s", resto) if p.strip()]
            anio = None
            for p in partes:
                if "/" in p:
                    anio = p.split("/")[-1].strip()
            for p in partes:
                if "/" not in p and anio:
                    p = f"{p}/{anio}"
                codigos.append(f"{prefijo}-{p}")
    return [
        {"codigo": c, "url": primer_url if i == 0 else None}
        for i, c in enumerate(codigos)
    ]


def leer_hoja(ws, tiene_cabecera):
    filas = []
    for r in range(4, ws.max_row + 1):
        od_cell = ws.cell(row=r, column=1)
        od_valor = od_cell.value
        if od_valor is None or str(od_valor).strip() == "":
            continue
        nro, anio, y_anexo = _parsear_od_numero(od_valor)
        if nro is None:
            continue

        exp_cell = ws.cell(row=r, column=2)
        exp_raw = exp_cell.value or ""
        exp_url = exp_cell.hyperlink.target if exp_cell.hyperlink else None
        expedientes = _parsear_expedientes(exp_raw, exp_url)
        origen, categoria = _origen_y_categoria(exp_url)

        contenido = re.sub(r"\s+", " ", ws.cell(row=r, column=3).value or "").strip()
        autor = OVERRIDES_AUTOR.get((nro, anio), _extraer_autor(contenido))

        firmantes_txt = ws.cell(row=r, column=4).value or ""
        comision = ws.cell(row=r, column=5).value if tiene_cabecera else None
        comision = comision.strip() if isinstance(comision, str) else comision

        od_link = od_cell.hyperlink.target if od_cell.hyperlink else None

        base = {
            "numero": str(nro),
            "periodo": anio,
            "origen": origen,
            "categoria": categoria,
            "autor": autor,
            "descripcion": contenido,
            "expedientes": expedientes,
            "comisionCabecera": comision or None,
            "fechaDictamen": None,
            "odLink": od_link,
        }
        base["comisiones"] = [comision] if comision else []

        if y_anexo and "ANEXO:" in firmantes_txt:
            principal, _, anexo = firmantes_txt.partition("ANEXO:")
            normal = dict(base, tipoOD="NORMAL", firmantesMayoria=_parsear_firmantes(principal))
            filas.append(normal)
            if anexo.strip():
                minoria = dict(base, tipoOD="ANEXO", firmantesMayoria=_parsear_firmantes(anexo))
                filas.append(minoria)
        elif y_anexo:
            normal = dict(base, tipoOD="NORMAL", firmantesMayoria=_parsear_firmantes(firmantes_txt))
            filas.append(normal)
            override_link = OVERRIDES_MINORIA_SIN_FIRMANTES.get((nro, anio))
            if override_link:
                minoria = dict(base, tipoOD="ANEXO", firmantesMayoria=[], odLink=override_link)
                filas.append(minoria)
        else:
            base["tipoOD"] = "NORMAL"
            base["firmantesMayoria"] = _parsear_firmantes(firmantes_txt)
            filas.append(base)
    return filas


def _fecha_str(v):
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y")
    v = str(v or "").strip()
    return v or None


def _parsear_giros(texto):
    """'DE A - DE B -' -> ['DE A', 'DE B'] (sin repetidos, orden estable,
    espacios colapsados: el sitio a veces mete dobles espacios)."""
    out = []
    for p in re.split(r"\s+-\s*", re.sub(r"\s+", " ", str(texto or "")).strip(" -")):
        p = p.strip(" -")
        if p and p not in out:
            out.append(p)
    return out


def leer_oficial(path):
    """-> {(numero, periodo, tipoOD): {"fecha": str|None, "giros": [str]}}"""
    if not os.path.exists(path):
        return {}
    ws = openpyxl.load_workbook(path, data_only=True).active
    res = {}
    for r in range(2, ws.max_row + 1):
        nro, per = ws.cell(row=r, column=2).value, ws.cell(row=r, column=1).value
        if nro is None or per is None:
            continue
        tipo = "ANEXO" if str(ws.cell(row=r, column=3).value or "").strip().upper().startswith("ANEXO") else "NORMAL"
        res[(int(nro), int(per), tipo)] = {
            "fecha": _fecha_str(ws.cell(row=r, column=7).value),
            "giros": _parsear_giros(ws.cell(row=r, column=6).value),
        }
    return res


def enriquecer_con_oficial(filas, oficial):
    sin_oficial, sin_fecha = [], []
    for f in filas:
        o = oficial.get((int(f["numero"]), f["periodo"], f["tipoOD"]))
        if not o:
            sin_oficial.append((f["numero"], f["tipoOD"]))
            continue
        f["fechaDictamen"] = o["fecha"]
        if not o["fecha"]:
            sin_fecha.append((f["numero"], f["tipoOD"]))
        # cabecera primero (la manda la planilla), después los demás giros;
        # los repetidos con otra grafía se unifican al resolver nombres
        # oficiales en generar_web.construir_ayuda_memoria.
        if o["giros"]:
            f["comisiones"] = ([f["comisionCabecera"]] if f["comisionCabecera"] else []) + o["giros"]
    return sin_oficial, sin_fecha


def main():
    wb = openpyxl.load_workbook(AYUDA_MEMORIA_PATH, data_only=True)
    filas = []
    for nombre in HOJAS:
        if nombre not in wb.sheetnames:
            print(f"AVISO: no se encontró la hoja '{nombre}', se omite")
            continue
        ws = wb[nombre]
        tiene_cabecera = nombre != "OD ACUERDOS"
        nuevas = leer_hoja(ws, tiene_cabecera)
        print(f"  {nombre}: {len(nuevas)} filas")
        filas.extend(nuevas)

    for f in filas:
        if f["categoria"] == "Acuerdo" and not f["comisionCabecera"]:
            f["comisionCabecera"] = "Acuerdos"
            f["comisiones"] = ["Acuerdos"]

    oficial = leer_oficial(ORDENES_DIA_OFICIAL_PATH)
    sin_oficial, sin_fecha = enriquecer_con_oficial(filas, oficial)

    claves = {(f["numero"], f["periodo"], f["tipoOD"]) for f in filas}
    for m in OD_MANUALES:
        if (m["numero"], m["periodo"], m["tipoOD"]) in claves:
            print(f"AVISO: OD {m['numero']}/{m['periodo']} ya está en la planilla; sacarla de OD_MANUALES")
            continue
        f = {k: v for k, v in m.items() if k != "firmantesTxt"}
        f["firmantesMayoria"] = _parsear_firmantes(m["firmantesTxt"])
        filas.append(f)

    filas.sort(key=lambda f: (f["periodo"], int(f["numero"])), reverse=True)

    os.makedirs(os.path.dirname(JSON_PATH), exist_ok=True)
    with open(JSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(filas, fh, ensure_ascii=False, indent=2)

    con_autor = sum(1 for f in filas if f["autor"])
    con_cabecera = sum(1 for f in filas if f["comisionCabecera"])
    print(f"Total: {len(filas)} órdenes del día")
    print(f"Con autor detectado: {con_autor} (sin autor: {len(filas) - con_autor} —")
    print("  esperado para mensajes del PEN, PL venidos en revisión de Diputados,")
    print("  notas de particulares y proyectos de 'varios señores/as senadores/as')")
    print(f"Con comisión cabecera: {con_cabecera}")
    print(f"Con fecha de dictamen: {sum(1 for f in filas if f['fechaDictamen'])} de {len(filas)}")
    if sin_oficial:
        print(f"AVISO: {len(sin_oficial)} OD de la planilla no están en {os.path.basename(ORDENES_DIA_OFICIAL_PATH)} "
              f"(sin fecha ni giros; bajar el export de nuevo): {sin_oficial}")
    if sin_fecha:
        print(f"AVISO: el export oficial trae la fecha vacía en: {sin_fecha}")


if __name__ == "__main__":
    main()
