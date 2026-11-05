#!/usr/bin/env python3
"""
scraper_od.py — Órdenes del Día (OD) del Senado → data/od.json
================================================================
Consulta https://www.senado.gob.ar/parlamentario/parlamentaria/ordenDelDia
para el año en curso y el anterior, itera todas las páginas de resultados y
extrae cada OD (número, año, tipo N/A, expedientes asociados, link al PDF).

La búsqueda por período se hace vía POST a ordenDelDiaResultado (la misma
sesión recuerda el filtro); la paginación posterior es GET ?page=N hasta que
una página no devuelve filas.

Es incremental: lee data/od.json existente y sólo agrega las OD que no están
ya presentes (clave: nro_od + anio_od + tipo_od).

Tolerante a fallos: si una página falla, se registra el error y se continúa.

Variables de entorno opcionales:
    TEST   "1" para modo de prueba: sólo la página 1 del año en curso,
           imprime resultados y no toca data/od.json.
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: faltan dependencias. Ejecutá: pip install -r requirements.txt")
    sys.exit(1)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
OD_JSON = os.path.join(DATA_DIR, "od.json")

TEST = os.getenv("TEST", "") == "1"

BASE_URL = "https://www.senado.gob.ar"
URL_OD = f"{BASE_URL}/parlamentario/parlamentaria/ordenDelDia"
URL_OD_RESULTADO = f"{BASE_URL}/parlamentario/parlamentaria/ordenDelDiaResultado"

# Ver nota en scraper_agenda.py: un User-Agent de navegador dispara el
# anti-bots del sitio; uno propio y honesto pasa sin problema. NO cambiarlo
# por uno de navegador.
HEADERS = {
    "User-Agent": "HSN-SistemaLegislativo/1.0 (+https://github.com/bonifaciomariano/hsn-sistema-legislativo)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}

PAUSA_ENTRE_REQUESTS = 1.0

# href de expediente: /parlamentario/comisiones/verExp/574.26/S/PD -> nro=574 anio=26 origen=S tipo=PD
RE_EXP_HREF = re.compile(r"/verExp/(\d+)\.(\d+)/([A-Z0-9.]+)/([A-Z0-9]+)", re.IGNORECASE)
RE_NRO_OD = re.compile(r"(\d+)\s*/\s*(\d+)")
RE_TIPO_OD = re.compile(r"\((N|A)\)")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def cargar_od_existente():
    if not os.path.exists(OD_JSON):
        return []
    with open(OD_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_od(od_lista):
    with open(OD_JSON, "w", encoding="utf-8") as f:
        json.dump(od_lista, f, ensure_ascii=False, indent=2)


def clave_od(entrada):
    return (entrada["nro_od"], entrada["anio_od"], entrada["tipo_od"])


def parsear_expediente_href(href):
    m = RE_EXP_HREF.search(href or "")
    if not m:
        return None
    nro = int(m.group(1))
    anio = 2000 + int(m.group(2))
    origen = m.group(3).replace(".", "")
    tipo = m.group(4)
    return {"nro": nro, "anio": anio, "tipo": tipo, "origen": origen,
            "url": BASE_URL + href if href.startswith("/") else href}


def parsear_fila(tr):
    tds = tr.find_all("td")
    if len(tds) < 4:
        return None

    texto_od = tds[0].get_text(" ", strip=True)
    m_nro = RE_NRO_OD.search(texto_od)
    m_tipo = RE_TIPO_OD.search(texto_od)
    if not m_nro:
        return None
    nro_od = int(m_nro.group(1))
    anio_od = int(m_nro.group(2))
    tipo_od = m_tipo.group(1) if m_tipo else "N"

    expedientes = []
    for a in tds[1].find_all("a", href=True):
        exp = parsear_expediente_href(a["href"])
        if exp:
            expedientes.append(exp)

    url_pdf = ""
    a_pdf = tds[3].find("a", href=True)
    if a_pdf:
        href = a_pdf["href"]
        url_pdf = BASE_URL + href if href.startswith("/") else href

    return {
        "nro_od": nro_od,
        "anio_od": anio_od,
        "tipo_od": tipo_od,
        "expedientes": expedientes,
        "url_pdf": url_pdf,
        "fecha": None,
    }


def parsear_pagina(html):
    soup = BeautifulSoup(html, "html.parser")
    tabla = soup.find("table", class_="table-bordered")
    if not tabla or not tabla.find("tbody"):
        return []
    filas = []
    for tr in tabla.find("tbody").find_all("tr"):
        entrada = parsear_fila(tr)
        if entrada:
            filas.append(entrada)
    return filas


def iniciar_sesion():
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get(URL_OD, timeout=30)
    return session


def buscar_periodo(session, anio):
    """POST del formulario de búsqueda filtrando por período (año); la sesión
    recuerda el filtro para las páginas GET subsiguientes."""
    return session.post(URL_OD_RESULTADO, data={
        "busqueda_orden[ordenDelDiaNumero]": "",
        "busqueda_orden[ordenDelDiaPeriodo]": str(anio),
        "busqueda_orden[palabra]": "",
        "tipoExpedientes": "",
    }, timeout=30)


def scrapear_anio(session, anio, solo_pagina_1=False):
    resultado = []
    log.info(f"  Período {anio}...")
    try:
        r = buscar_periodo(session, anio)
        r.raise_for_status()
    except Exception as e:
        log.error(f"  ERROR al buscar período {anio}: {e}")
        return resultado

    pagina = 1
    while True:
        try:
            if pagina == 1:
                html = r.text
            else:
                resp = session.get(f"{URL_OD_RESULTADO}?page={pagina}", timeout=30)
                resp.raise_for_status()
                html = resp.text
        except Exception as e:
            log.error(f"  ERROR en página {pagina} (año {anio}): {e}")
            break

        filas = parsear_pagina(html)
        if not filas:
            break
        resultado.extend(filas)
        log.info(f"    página {pagina}: {len(filas)} filas")

        if solo_pagina_1:
            break
        pagina += 1
        time.sleep(PAUSA_ENTRE_REQUESTS)

    return resultado


def main():
    log.info("=" * 60)
    log.info("scraper_od iniciado" + (" (TEST)" if TEST else ""))

    anio_actual = datetime.now().year
    session = iniciar_sesion()

    if TEST:
        filas = scrapear_anio(session, anio_actual, solo_pagina_1=True)
        log.info(f"  -> {len(filas)} filas en la página 1 de {anio_actual}")
        print(json.dumps(filas, ensure_ascii=False, indent=2))
        return

    existentes = cargar_od_existente()
    claves_existentes = {clave_od(e) for e in existentes}
    log.info(f"  → {len(existentes)} OD ya en data/od.json")

    nuevas = []
    vistas = set()
    for anio in (anio_actual, anio_actual - 1):
        filas = scrapear_anio(session, anio)
        for f in filas:
            k = clave_od(f)
            if k in vistas:
                continue
            vistas.add(k)
            if k not in claves_existentes:
                nuevas.append(f)

    od_final = existentes + nuevas
    guardar_od(od_final)
    log.info(f"  → {len(nuevas)} OD nuevas agregadas")
    log.info(f"  → TOTAL en od.json: {len(od_final)}")
    log.info("scraper_od finalizado.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
