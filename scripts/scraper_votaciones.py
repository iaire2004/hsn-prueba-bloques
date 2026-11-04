#!/usr/bin/env python3
"""
scraper_votaciones.py — Votaciones nominales del Senado → data/votaciones.json
================================================================================
Fuente: https://www.senado.gob.ar/votaciones/actas
  - El listado de actas del período viene completo en el HTML (la tabla
    #actasTable se pagina del lado del navegador). Se pide por POST con el
    año como filtro (busqueda_actas[anio]).
  - Cada acta tiene un detalle en /votaciones/detalleActa/{id} con el voto
    nominal de cada senador (AFIRMATIVO / NEGATIVO / ABSTENCIÓN / AUSENTE).

Sólo se guardan las votaciones EN GENERAL (y EN GENERAL Y EN PARTICULAR):
las votaciones en particular, mociones de orden y otras se descartan.

Es incremental: no vuelve a pedir el detalle de actas ya guardadas.
Tolerante a fallos: si un detalle falla, se registra y se sigue; la próxima
corrida lo reintenta.

Variables de entorno:
    HSN_DATA_OUT   carpeta de salida (default: ./data)
    HSN_ANIO       año a consultar (default: año actual)
    TEST           "1": sólo muestra qué haría, sin escribir
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
    print("ERROR: faltan dependencias (requests, beautifulsoup4).")
    sys.exit(1)

BASE_URL = "https://www.senado.gob.ar"
URL_ACTAS = f"{BASE_URL}/votaciones/actas"
URL_DETALLE = f"{BASE_URL}/votaciones/detalleActa/{{id}}"

OUT_DIR = os.getenv("HSN_DATA_OUT", "data")
SALIDA = os.path.join(OUT_DIR, "votaciones.json")
ANIO = int(os.getenv("HSN_ANIO", datetime.now().year))
TEST = os.getenv("TEST", "") == "1"

# Igual que los demás scrapers del sistema: un User-Agent de navegador dispara
# el anti-bots del sitio; uno propio y honesto pasa. NO cambiarlo.
HEADERS = {
    "User-Agent": "HSN-SistemaLegislativo/1.0 (+https://github.com/bonifaciomariano/hsn-sistema-legislativo)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}
PAUSA = 3.0            # entre pedidos de detalle (el sitio limita ráfagas)
MAX_DETALLES_POR_CORRIDA = 25   # lo que falte se completa en la corrida siguiente
FRASE_BLOQUEO = "No pudimos procesar su solicitud"
TIPOS_GENERALES = {"EN GENERAL", "EN GENERAL Y EN PARTICULAR"}
VOTOS = {"AFIRMATIVO": "a", "NEGATIVO": "n", "ABSTENCION": "b", "AUSENTE": "x"}

RE_ID = re.compile(r"/votaciones/detalleActa/(\d+)")
RE_FECHA = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
RE_OD = re.compile(r"O\.?\s*D\.?\s*(\d+)\s*/\s*(\d+)", re.IGNORECASE)
RE_EXP = re.compile(r"/verExp/(\d+)\.(\d+)/([A-Z0-9.]+)/([A-Z0-9]+)", re.IGNORECASE)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger("votaciones")


def _limpio(s):
    return re.sub(r"\s+", " ", s or "").strip()


def _sin_tildes(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def parsear_listado(html):
    """Devuelve las actas del listado (todas las filas de #actasTable)."""
    soup = BeautifulSoup(html, "html.parser")
    tabla = soup.find("table", id="actasTable")
    if not tabla or not tabla.find("tbody"):
        return []
    actas = []
    for tr in tabla.find("tbody").find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 8:
            continue
        a_det = tr.find("a", href=RE_ID)
        if not a_det:
            continue
        id_acta = int(RE_ID.search(a_det["href"]).group(1))
        m = RE_FECHA.search(_limpio(tds[0].get_text(" ")))
        if not m:
            continue
        fecha = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"  # DD-MM-AAAA

        celda_titulo = tds[2]
        # título = texto de la celda antes del enlace "Ver Expedientes"
        partes = []
        for nodo in celda_titulo.children:
            if getattr(nodo, "name", None) in ("a", "div"):
                break
            if isinstance(nodo, str):
                partes.append(nodo)
        titulo = _limpio(" ".join(partes))
        titulo = re.sub(r"[\s(]+$", "", titulo)   # el sitio deja un "(" antes de la lista de expedientes
        oculto = celda_titulo.find("div", class_="expedientesOcultos")
        ods, exps = [], []
        if oculto:
            for a in oculto.find_all("a", href=True):
                txt = _limpio(a.get_text(" "))
                mo = RE_OD.search(txt)
                if mo:
                    ods.append({"nro": int(mo.group(1)), "anio": int(mo.group(2))})
                me = RE_EXP.search(a["href"])
                if me:
                    exps.append({"nro": int(me.group(1)), "anio": int(me.group(2)),
                                 "origen": me.group(3).upper(), "tipo": me.group(4).upper(),
                                 "texto": txt})
        resultado = _limpio(tds[4].get_text(" ")).replace("positivo", "").replace("negativo", "").strip()
        actas.append({
            "id": id_acta,
            "fecha": fecha,
            "nro_acta": _limpio(tds[1].get_text()),
            "titulo": titulo,
            "tipo": _limpio(tds[3].get_text()).upper(),
            "resultado": resultado.upper(),
            "mayoria": _limpio(tds[6].get_text()).upper(),
            "ods": ods,
            "expedientes": exps,
        })
    return actas


def parsear_detalle(html):
    """Devuelve (hora, votos[{senador, bloque, provincia, voto}]) del detalle."""
    soup = BeautifulSoup(html, "html.parser")
    tabla = soup.find("table", id="tabla")
    if not tabla:
        return None, []
    hora = None
    m = re.search(r"\d{2}/\d{2}/\d{4}\s*-\s*(\d{1,2}:\d{2})", soup.get_text(" "))
    if m:
        hora = m.group(1)
    votos = []
    cuerpo = tabla.find("tbody") or tabla
    for tr in cuerpo.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 5:
            continue
        clave = _sin_tildes(_limpio(tds[4].get_text())).upper()
        voto = VOTOS.get(clave)
        if voto is None:
            log.warning("voto no reconocido: %r", clave)
            continue
        votos.append({
            "senador": _limpio(tds[1].get_text()),
            "bloque": _limpio(tds[2].get_text()).upper(),
            "provincia": _limpio(tds[3].get_text()).upper(),
            "voto": voto,
        })
    return hora, votos


def resumir_por_bloque(votos):
    """{bloque: {a, n, b, x}} — afirmativos, negativos, abstenciones, ausentes."""
    res = {}
    for v in votos:
        c = res.setdefault(v["bloque"], {"a": 0, "n": 0, "b": 0, "x": 0})
        c[v["voto"]] += 1
    return res


def cargar_existente():
    if not os.path.exists(SALIDA):
        return {"anio": ANIO, "actas": []}
    with open(SALIDA, encoding="utf-8") as f:
        return json.load(f)


def main():
    s = requests.Session()
    s.headers.update(HEADERS)

    r = s.post(URL_ACTAS, data={"busqueda_actas[anio]": str(ANIO), "busqueda_actas[titulo]": ""}, timeout=60)
    r.raise_for_status()
    actas = parsear_listado(r.text)
    if not actas:
        # el sitio puede cambiar el formulario: probar el listado por defecto
        r = s.get(URL_ACTAS, timeout=60)
        r.raise_for_status()
        actas = parsear_listado(r.text)
    log.info("Actas en el listado %s: %d", ANIO, len(actas))
    if not actas:
        log.error("No se pudo leer el listado de actas; no se modifica nada.")
        sys.exit(1)

    generales = [a for a in actas if a["tipo"] in TIPOS_GENERALES and a["fecha"].endswith(str(ANIO))]
    log.info("Votaciones en general: %d", len(generales))

    previo = cargar_existente()
    guardadas = {a["id"]: a for a in previo.get("actas", [])}
    nuevas = [a for a in generales if a["id"] not in guardadas]
    log.info("Pendientes de detalle: %d", len(nuevas))
    if TEST:
        for a in nuevas[:5]:
            print(a)
        return

    errores = 0
    for a in nuevas[:MAX_DETALLES_POR_CORRIDA]:
        time.sleep(PAUSA)
        try:
            d = s.get(URL_DETALLE.format(id=a["id"]), timeout=60)
            d.raise_for_status()
            if FRASE_BLOQUEO in d.text:
                # El sitio frenó el acceso: no se insiste ni se reintenta en esta
                # corrida. Lo ya guardado se conserva y se completa en la próxima.
                log.warning("El sitio limitó el acceso (acta %s); corto la corrida.", a["id"])
                break
            hora, votos = parsear_detalle(d.text)
            if not votos:
                raise ValueError("detalle sin votos")
            a["hora"] = hora
            a["votos"] = votos
            a["por_bloque"] = resumir_por_bloque(votos)
            guardadas[a["id"]] = a
        except Exception as e:  # noqa: BLE001 - se reintenta en la próxima corrida
            errores += 1
            log.warning("acta %s: %s", a["id"], e)

    def clave(a):
        d, m, y = a["fecha"].split("-")
        return (y, m, d, a["id"])

    salida = {
        "anio": ANIO,
        "actualizado": datetime.now().strftime("%d-%m-%Y %H:%M"),
        "fuente": URL_ACTAS,
        "total_generales": len(generales),
        "actas": sorted(guardadas.values(), key=clave),
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)
    log.info("Guardadas %d actas (%d errores)", len(salida["actas"]), errores)


if __name__ == "__main__":
    main()
