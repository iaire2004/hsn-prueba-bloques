#!/usr/bin/env python3
"""sanciones_senado.py — Sanciones PROPIAS de este repo (data/sanciones.json), leídas del Boletín de
Novedades del Senado.

  1. Si data/sanciones.json no existe, se siembra una vez con el del repo del sistema legislativo (si
     está disponible en ./source). Es incremental: lee solo los boletines nuevos.
  2. Corre scraper_sanciones.py (lee los PDF del Boletín de Novedades de cada sesión).
  3. Resguardo: si falla o el archivo queda con menos ítems que antes, se vuelve a la copia anterior.
     Nunca frena el workflow.

Variables: HSN_SOURCE (solo para sembrar), SANCIONES_REPROCESAR (ej. "7/26,8/26" o "TODOS").
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
SANC = os.path.join(DATA, "sanciones.json")
PROC = os.path.join(DATA, "sanciones_procesados.json")


def cantidad(ruta):
    try:
        return len(json.load(open(ruta, encoding="utf-8")))
    except Exception:
        return None


def sembrar(archivo):
    destino = os.path.join(DATA, archivo)
    origen = os.path.join(SOURCE, "data", archivo)
    if os.path.exists(destino) or not os.path.exists(origen):
        return
    os.makedirs(DATA, exist_ok=True)
    shutil.copyfile(origen, destino)
    print("Sembrado data/%s con el de la fuente (solo la primera vez)." % archivo)


def main():
    sembrar("sanciones.json")
    sembrar("sanciones_procesados.json")
    antes = cantidad(SANC)
    previos = {}
    for ruta in (SANC, PROC):
        if os.path.exists(ruta):
            previos[ruta] = ruta + ".previo"
            shutil.copyfile(ruta, previos[ruta])
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "scraper_sanciones.py")], cwd=ROOT)
        ok = r.returncode == 0
    except Exception as e:
        print("AVISO  No se pudo correr scraper_sanciones.py (%s)." % e)
        ok = False
    despues = cantidad(SANC)
    reprocesa = bool(os.environ.get("SANCIONES_REPROCESAR", "").strip())
    if not ok or (antes and (despues is None or (not reprocesa and despues < antes))):
        print("AVISO  Se conservan las sanciones anteriores (%s ítems)." % antes)
        for ruta, copia in previos.items():
            shutil.copyfile(copia, ruta)
        despues = antes
    for copia in previos.values():
        try:
            os.remove(copia)
        except OSError:
            pass
    print("Sanciones propias: %s antes, %s después." % (antes, despues))
    return 0


if __name__ == "__main__":
    sys.exit(main())
