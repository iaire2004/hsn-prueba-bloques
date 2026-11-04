#!/usr/bin/env python3
"""verificar_paginas.py — chequeos de cordura de las 14 páginas por bloque, después de generarlas.

Lee la variable `B` de cada <bloque>/index.html y la compara con reglas simples y con la
versión anterior publicada (git HEAD). Si algo es grave sale con código 1, y el workflow NO
publica (las páginas ya publicadas quedan como estaban). Los avisos leves sólo se informan.

    python scripts/verificar_paginas.py [carpeta_de_salida]      (por defecto: .)
Variable: CAIDA_MAX (por defecto 0.30) = caída máxima tolerada de proyectos entre corridas.
"""
import json
import os
import subprocess
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
CAIDA_MAX = float(os.getenv("CAIDA_MAX", "0.30"))
ESPERADOS = 14


def leer_B(html):
    i = html.index("var B =") + 7
    j = html.index("\n", i)
    return json.loads(html[i:j].rstrip().rstrip(";"))


def previo(slug):
    try:
        h = subprocess.run(["git", "show", "HEAD:%s/index.html" % slug], cwd=OUT, capture_output=True,
                           text=True, encoding="utf-8", check=True).stdout
        return leer_B(h)
    except Exception:
        return None


def cruce_actas(avisos):
    """Cruce de control: cada orden del día aprobada en un acta de votación (EN GENERAL) debe
    tener sus proyectos del Senado marcados como aprobados. Sólo avisa."""
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fuente = os.environ.get("HSN_SOURCE", os.path.join(raiz, "source"))
    try:
        actas = json.load(open(os.path.join(raiz, "data", "votaciones.json"), encoding="utf-8"))["actas"]
        proy = json.load(open(os.path.join(fuente, "data", "proyectos.json"), encoding="utf-8"))
        proy = proy if isinstance(proy, list) else proy.get("proyectos", [])
    except Exception as e:
        avisos.append("Cruce con actas omitido (%s)" % e)
        return 0
    aprobadas = {}
    for a in actas:
        if a.get("resultado") != "AFIRMATIVO":
            continue
        for od in a.get("ods") or []:
            aprobadas[(od.get("nro"), od.get("anio"))] = a.get("fecha")
    n = 0
    for p in proy:
        if p.get("origen") != "S":
            continue
        for od in p.get("od_trazabilidad") or []:
            k = (od.get("nro"), od.get("anio"))
            if k not in aprobadas:
                continue
            aprobado = p.get("badge_sancionado") or any(
                x.get("codigo") == "AP" for x in (p.get("sanciones_trazabilidad") or []))
            if not aprobado:
                avisos.append("Acta del %s aprobó la OD %s/%s pero S-%s/%s no figura como aprobado"
                              % (aprobadas[k], k[0], k[1], p.get("nro"), p.get("anio")))
            n += 1
    print("Cruce con actas: %d proyectos del Senado en órdenes del día aprobadas revisados." % n)
    return n


def main():
    graves, avisos = [], []
    slugs = sorted(d for d in os.listdir(OUT) if os.path.isfile(os.path.join(OUT, d, "index.html"))
                   and d not in ("source", "salida"))
    paginas = {}
    for s in slugs:
        try:
            paginas[s] = leer_B(open(os.path.join(OUT, s, "index.html"), encoding="utf-8").read())
        except Exception:
            continue  # no es página de bloque
    if len(paginas) != ESPERADOS:
        graves.append("Se esperaban %d páginas de bloque y hay %d" % (ESPERADOS, len(paginas)))
    for s, b in paginas.items():
        n = b["bloque"]
        if not b["senadores"]:
            graves.append("%s: sin senadores" % n)
        ids = [p["id"] for p in b["proyectos"]]
        if len(ids) != len(set(ids)):
            graves.append("%s: proyectos repetidos en el listado" % n)
        if b["total"] != len(ids):
            graves.append("%s: el total (%s) no coincide con el listado (%s)" % (n, b["total"], len(ids)))
        apr = {a["id"] for a in b["aprobados"]}
        mal = sorted(apr & {x["id"] for x in b["por_caducar"]})
        if mal:
            graves.append("%s: aprobados que figuran como por caducar: %s" % (n, ", ".join(mal)))
        if len({x["id"] for x in b["aprobados"]}) != len(b["aprobados"]):
            avisos.append("%s: aprobados repetidos" % n)
        for x in b["senadores"]:
            if not x.get("provincia"):
                avisos.append("%s: senador/a sin provincia: %s" % (n, x.get("nombre", "?")))
        pv = previo(s)
        if pv and pv.get("total"):
            caida = 1 - b["total"] / pv["total"]
            if caida > CAIDA_MAX:
                graves.append("%s: los proyectos bajaron de %s a %s (%.0f%%)" % (n, pv["total"], b["total"], caida * 100))
            if len(pv["senadores"]) != len(b["senadores"]):
                avisos.append("%s: cambió la cantidad de senadores (%s → %s)" % (n, len(pv["senadores"]), len(b["senadores"])))
    cruce_actas(avisos)
    for a in avisos:
        print("AVISO  " + a)
    for g in graves:
        print("::error::GRAVE  " + g)
    print("Verificación: %d páginas, %d graves, %d avisos." % (len(paginas), len(graves), len(avisos)))
    return 1 if graves else 0


if __name__ == "__main__":
    sys.exit(main())
