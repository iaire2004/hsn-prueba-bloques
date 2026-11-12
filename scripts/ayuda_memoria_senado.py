#!/usr/bin/env python3
"""ayuda_memoria_senado.py — Ayuda Memoria PROPIA de este repo (data/ayuda_memoria_auto.json).

Las páginas usan este archivo (data/ayuda_memoria.json, copia de ayuda_memoria_auto.json). Se arma
directo del Senado.

La Ayuda Memoria = las Órdenes del Día cuyo ESTADO en el Senado es PENDIENTE; los datos salen del PDF
de cada OD. Usa los datos propios (data/od.json y data/proyectos.json de este repo).

  1. Siembra data/estado_od.json con el de la fuente si no existe (así no hay que consultar ~400
     fichas la primera vez; después solo se consultan las pendientes y las nuevas).
  2. Corre actualizar_ayuda_memoria.py (copia del de la fuente). Los PDF van a /tmp/pdfs_od.
  3. Resguardo: si falla o queda sin fichas, se conserva la copia anterior. Nunca frena el workflow.

Variables: HSN_SOURCE, PDFS_OD (carpeta de PDF, /tmp/pdfs_od por defecto).
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
SOURCE = os.environ.get("HSN_SOURCE", os.path.join(ROOT, "source"))
PDFS = os.environ.get("PDFS_OD", "/tmp/pdfs_od")
SALIDA = os.path.join(DATA, "ayuda_memoria_auto.json")


def cantidad(ruta):
    try:
        return len(json.load(open(ruta, encoding="utf-8")))
    except Exception:
        return None


def main():
    os.makedirs(DATA, exist_ok=True)
    for archivo in ("od.json", "proyectos.json"):
        if not os.path.exists(os.path.join(DATA, archivo)):
            print("AVISO  Falta data/%s propio: la Ayuda Memoria propia no se arma." % archivo)
            return 0
    est = os.path.join(DATA, "estado_od.json")
    if not os.path.exists(est):
        origen = os.path.join(SOURCE, "data", "estado_od.json")
        if os.path.exists(origen):
            shutil.copyfile(origen, est)
            print("Sembrado data/estado_od.json con el de la fuente.")
    antes = cantidad(SALIDA)
    copia = SALIDA + ".previo"
    if os.path.exists(SALIDA):
        shutil.copyfile(SALIDA, copia)
    try:
        r = subprocess.run([sys.executable, "-u", os.path.join(HERE, "actualizar_ayuda_memoria.py"),
                            "--pdfs", PDFS], cwd=ROOT)
        ok = r.returncode == 0
    except Exception as e:
        print("AVISO  No se pudo correr actualizar_ayuda_memoria.py (%s)." % e)
        ok = False
    despues = cantidad(SALIDA)
    if (not ok or not despues) and os.path.exists(copia):
        print("AVISO  Se conserva la Ayuda Memoria anterior.")
        shutil.copyfile(copia, SALIDA)
        despues = antes
    try:
        os.remove(copia)
    except OSError:
        pass
    if despues:
        shutil.copyfile(SALIDA, os.path.join(DATA, "ayuda_memoria.json"))  # es la que usan las páginas
    print("Ayuda Memoria propia: %s fichas antes, %s después." % (antes, despues))
    return 0


if __name__ == "__main__":
    sys.exit(main())
