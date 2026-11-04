#!/usr/bin/env python3
"""bicamerales_senado.py — Comisiones BICAMERALES (senadores + diputados) leídas del Senado.

Las páginas por bloque las muestran en un apartado aparte (el repo del sistema legislativo las
ignora a propósito). Una consulta por comisión (22), con pausa; resultado en data/bicamerales.json:

  [{"id": 105, "nombre": "...", "tipo": "Permanente", "miembros": [
      {"nombre": "APELLIDO, Nombre", "cargo": "Presidente", "camara": "SENADO",
       "bloque": "UCR - UNIÓN CÍVICA RADICAL", "vacante": false}, ...]}]

Resguardos: si una comisión no responde o no trae la tabla, se conserva lo que había de esa
comisión; si fallan más de 8, no se escribe nada. La tabla del Senado trae las columnas
Foto · Nombre y apellido · Cargo · Cámara · Bloque · Distrito.

Variables: BICAMERALES_LOCAL (carpeta con <ID>.html para pruebas sin red), TEST=1 (no escribe).
"""
import json
import os
import re
import sys
import time
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "bicamerales.json")
SENADORES = os.path.join(DATA, "senadores.json")
URL = "https://www.senado.gob.ar/parlamentario/comisiones/info/{id}"
UA = ("HSN-Sistema-Legislativo/1.0 (herramienta interna de la Prosecretaria Parlamentaria; "
      "1 consulta por comision por corrida)")
LOCAL = os.getenv("BICAMERALES_LOCAL", "").strip()
TEST = os.getenv("TEST", "") == "1"

# (ID en senado.gob.ar, tipo, nombre) — listado oficial "Comisiones Bicamerales"
BICAMERALES = [
    (117, "Permanente", "Bicameral Asesora de la Federación Argentina de Municipios (Ley 24.807)"),
    (118, "Permanente", "Bicameral de Control de los Fondos de la Seguridad Social (Ley 26.425)"),
    (315, "Permanente", "Bicameral de Reforma del Estado y del Seguimiento de las Privatizaciones (Ley 23.696)"),
    (104, "Permanente", "Bicameral Permanente de Fiscalización de los Organismos y Actividades de Inteligencia (Ley 25.520)"),
    (107, "Permanente", "Bicameral Permanente de Fiscalización de los Órganos y Actividades de Seguridad Interior (Ley 24.059)"),
    (103, "Permanente", "Bicameral Permanente de la Defensoría del Pueblo"),
    (106, "Permanente", "Bicameral Permanente de Promoción y Seguimiento de la Comunicación Audiovisual, las Tecnologías de las Telecomunicaciones y la Digitalización (Ley 26.522)"),
    (114, "Permanente", "Bicameral Permanente de Seguimiento de Contratos de Participación Público-Privada (Ley 27.328)"),
    (111, "Permanente", "Bicameral Permanente de Seguimiento y Control de la Gestión de Contratación y de Pago de la Deuda Exterior de la Nación (Ley 27.249)"),
    (110, "Permanente", "Bicameral Permanente de Seguimiento y Control del Ministerio Público de la Nación (Ley 24.946)"),
    (105, "Permanente", "Bicameral Permanente de Trámite Legislativo (Ley 26.122)"),
    (115, "Permanente", "Bicameral Permanente del Defensor de los Derechos de Niñas, Niños y Adolescentes (Ley 26.061)"),
    (108, "Permanente", "Bicameral Permanente del Digesto Jurídico Argentino (Ley 26.939)"),
    (112, "Permanente", "Bicameral Permanente Interparlamentaria Argentino-Mexicana"),
    (100, "Permanente", "Bicameral Permanente Mixta Revisora de Cuentas"),
    (113, "Permanente", "Bicameral Permanente Parlamentaria Conjunta Argentino-Chilena"),
    (116, "Permanente", "De Integración Bilateral y Cooperación entre la República Argentina y la República Federativa del Brasil"),
    (388, "Especial", "De Supervisión Parlamentaria de la Oficina de Presupuesto del Congreso (Ley 27.343)"),
    (382, "Especial", "Bicameral para la Reforma Tributaria (Ley 27.260)"),
    (379, "Especial", "Bicameral de Monitoreo e Implementación del Código Procesal Penal Federal (Ley 27.063)"),
    (331, "Especial", "Bicameral Ciudad de Buenos Aires (Ley 24.588)"),
    (380, "Especial", "Administradora del «Edificio del Molino» (Ley 27.009)"),
]


def sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")


def clave(n):
    return " ".join(sorted(sin_tildes((n or "").upper()).replace(",", " ").split()))


def formato_nombre(web):
    """'ENRIQUE MARTÍN  GOERLING LARA' (nombre, DOS espacios, apellido) -> 'GOERLING LARA, Enrique Martín'."""
    partes = [p.strip() for p in re.split(r"\s{2,}", web.strip()) if p.strip()]
    if len(partes) >= 2:
        return "%s, %s" % (" ".join(partes[1:]).upper(), partes[0].title())
    return web.strip().upper()


def cargo_de(txt):
    t = sin_tildes((txt or "").upper())
    if t.startswith("PRESIDENT"):
        return "Presidente"
    if t.startswith("VICEPRESIDENT"):
        m = re.search(r"(\d)", t)
        return "Vicepresidente" + (" %s°" % m.group(1) if m else "")
    if t.startswith("SECRETARI"):
        return "Secretario"
    return ""  # vocal u otro


def obtener(cid):
    if LOCAL:
        p = os.path.join(LOCAL, "%d.html" % cid)
        return open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
    import requests
    r = requests.get(URL.format(id=cid), headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    return r.text


def parsear(html, padron_por_clave):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for t in soup.find_all("table"):
        filas = t.find_all("tr")
        if not filas:
            continue
        enc = [c.get_text(" ", strip=True).lower() for c in filas[0].find_all(["th", "td"])]
        if "cargo" in enc and "bloque" in enc and any(e.startswith("nombre") for e in enc):
            i_n = next(i for i, e in enumerate(enc) if e.startswith("nombre"))
            i_c, i_b = enc.index("cargo"), enc.index("bloque")
            i_cam = next((i for i, e in enumerate(enc) if e.startswith("c") and "mara" in e), None)
            out = []
            for tr in filas[1:]:
                td = tr.find_all("td")
                if len(td) <= max(i_n, i_c, i_b):
                    continue
                nombre = re.sub(r"[\r\n\t]+", " ", td[i_n].get_text(" ", strip=False).replace("\xa0", " ")).strip()
                vac = "VACANTE" in nombre.upper()
                camara = sin_tildes(td[i_cam].get_text(" ", strip=True).upper()) if i_cam is not None and len(td) > i_cam else ""
                bloque = td[i_b].get_text(" ", strip=True)
                if not vac and camara.startswith("SENAD"):
                    ref = padron_por_clave.get(clave(nombre))
                    if ref:
                        bloque = ref.get("bloque") or bloque
                    nombre = formato_nombre(nombre) if not ref else ref["_k"]
                elif not vac:
                    nombre = formato_nombre(nombre)
                out.append({"nombre": nombre if not vac else "VACANTE", "cargo": cargo_de(td[i_c].get_text(" ", strip=True)),
                            "camara": "SENADO" if camara.startswith("SENAD") else ("DIPUTADOS" if camara.startswith("DIPUT") else camara),
                            "bloque": bloque, "vacante": vac})
            return out
    return None


def main():
    try:
        padron = json.load(open(SENADORES, encoding="utf-8"))
    except Exception:
        padron = {}
    por_clave = {}
    for k, v in padron.items():
        d = dict(v)
        a, _, b = k.partition(",")
        d["_k"] = "%s, %s" % (a.strip(), b.strip().title()) if b else k
        por_clave[clave(k)] = d
    previas = {}
    if os.path.exists(OUT):
        try:
            previas = {c["id"]: c for c in json.load(open(OUT, encoding="utf-8"))}
        except Exception:
            pass
    nuevas, fallos, leidas = [], [], 0
    for cid, tipo, nombre in BICAMERALES:
        miembros = None
        try:
            html = obtener(cid)
            miembros = parsear(html, por_clave) if html else None
            if miembros is None:
                fallos.append("%s (%d): sin tabla de integrantes" % (nombre[:50], cid))
        except Exception as e:
            fallos.append("%s (%d): %s" % (nombre[:50], cid, e))
        if miembros is None:
            if cid in previas:
                nuevas.append(previas[cid])   # se conserva lo anterior
        else:
            leidas += 1
            nuevas.append({"id": cid, "nombre": nombre, "tipo": tipo, "miembros": miembros})
        if not LOCAL:
            time.sleep(1.5)
    print("Bicamerales leídas OK: %d de %d" % (leidas, len(BICAMERALES)))
    for f in fallos:
        print("AVISO  no se pudo leer: " + f)
    for c in nuevas:
        pres = [m["nombre"] + " (" + m["camara"] + ")" for m in c["miembros"] if m["cargo"] == "Presidente" and not m["vacante"]]
        print("  %-3d %s → %s" % (c["id"], c["nombre"][:60], ", ".join(pres) or "sin presidente"))
    if len(fallos) > 8:
        print("AVISO  Demasiadas comisiones sin leer: no se escribe nada.")
        return 0
    if TEST:
        print("TEST=1: no se escribe.")
        return 0
    os.makedirs(DATA, exist_ok=True)
    json.dump(nuevas, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
