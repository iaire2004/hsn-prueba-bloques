#!/usr/bin/env python3
"""prueba_desde_cero.py — ¿Se pueden reconstruir agenda y OD SOLO desde el Senado, sin la base de Mariano?

Corre los scrapers en una carpeta temporal con data/ VACÍA (sin sembrar nada de la fuente) y compara
lo que logran bajar contra lo que hay hoy en data/ (que se sembró con la fuente). NO modifica data/.

Resultado por pieza: cuántas OD / reuniones se reconstruyen desde cero, cuáles faltan y desde qué
fecha llega el historial. Si desde cero se obtiene todo, esa pieza ya es independiente.
Nunca frena el workflow.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")


def cargar(base, nombre):
    try:
        return json.load(open(os.path.join(base, "data", nombre), encoding="utf-8"))
    except Exception:
        return None


def correr_en_vacio(script, extra_data=()):
    tmp = tempfile.mkdtemp(prefix="cero_")
    os.makedirs(os.path.join(tmp, "scripts"))
    os.makedirs(os.path.join(tmp, "data"))
    shutil.copy(os.path.join(HERE, script), os.path.join(tmp, "scripts", script))
    for n in extra_data:  # solo lo necesario para resolver nombres; no es historial de Mariano
        if os.path.exists(os.path.join(DATA, n)):
            shutil.copy(os.path.join(DATA, n), os.path.join(tmp, "data", n))
    r = subprocess.run([sys.executable, os.path.join(tmp, "scripts", script)], cwd=tmp,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return tmp, r.returncode


def reuniones(d):
    lst = d.get("reuniones", []) if isinstance(d, dict) else (d or [])
    return {(r.get("fecha"), r.get("hora"), str(r.get("comisiones"))) for r in lst}


def fechas(claves):
    f = sorted(k[0] for k in claves if k[0])
    return (f[0], f[-1]) if f else ("-", "-")


def od():
    print("== Órdenes del día, desde cero ==")
    tmp, rc = correr_en_vacio("scraper_od.py")
    c, base = cargar(tmp, "od.json"), cargar(ROOT, "od.json")
    if c is None or rc != 0 or not c:
        print("AVISO  No se pudo reconstruir desde cero (código %s): sin resultado, no se concluye nada." % rc)
        shutil.rmtree(tmp, ignore_errors=True)
        return
    k = lambda lst: {(o.get("nro_od"), o.get("anio_od"), o.get("tipo_od")) for o in lst}
    a, b = k(c), k(base or [])
    print("Desde cero: %d OD | En data/ (sembrado): %d OD" % (len(a), len(b)))
    print("Faltan desde cero: %d | Sobran desde cero: %d" % (len(b - a), len(a - b)))
    print("RESULTADO: %s" % ("INDEPENDIENTE (coincide)" if a == b else "hay diferencias, ver arriba"))
    shutil.rmtree(tmp, ignore_errors=True)


def agenda():
    print("== Agenda, desde cero ==")
    tmp, rc = correr_en_vacio("scraper_agenda.py", ("comisiones.json",))
    c, base = cargar(tmp, "agenda.json"), cargar(ROOT, "agenda.json")
    if c is None or rc != 0 or not reuniones(c):
        print("AVISO  No se pudo reconstruir desde cero (código %s): sin resultado, no se concluye nada." % rc)
        shutil.rmtree(tmp, ignore_errors=True)
        return
    a, b = reuniones(c), reuniones(base or [])
    print("Desde cero: %d reuniones (fechas %s a %s)" % ((len(a),) + fechas(a)))
    print("En data/ (sembrado): %d reuniones (fechas %s a %s)" % ((len(b),) + fechas(b)))
    print("Faltan desde cero: %d | Sobran desde cero: %d" % (len(b - a), len(a - b)))
    print("RESULTADO: %s" % ("INDEPENDIENTE (coincide)" if a == b else
                             "el historial anterior NO se reconstruye solo; se necesita la base sembrada"))
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    try:
        od()
        agenda()
    except Exception as e:
        print("AVISO  La prueba falló (%s). No afecta nada." % e)
    sys.exit(0)
