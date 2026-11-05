#!/usr/bin/env python3
"""proyectos_senado.py — Proyectos (expedientes) PROPIOS de este repo (data/proyectos.json).

MODO SOMBRA: las páginas siguen usando los proyectos del repo del sistema legislativo; esta copia
se actualiza directo del Senado y el verificador la compara con la de la fuente.

  1. Si data/proyectos.json no existe, se siembra con el de la fuente (es incremental: sin esa base
     habría que bajar miles de expedientes). Lo mismo con data/acuerdos.json.
  2. El padrón con el que se asignan bloques y provincias es el PROPIO (data/senadores.json, que
     arma padron_senadores.py); si no existe se usa el de la fuente.
  3. Se corre scraper_proyectos.py (copia del de la fuente): busca los expedientes ingresados en los
     últimos días (VENTANA_DIAS, 30 por defecto), procesa los que no están, y re-visita un lote de
     expedientes abiertos para actualizar archivo / caducidad / sanción (LOTE_REVISION).
  4. Resguardo: si el archivo resultante tiene claramente menos proyectos que antes (más de 2%),
     se vuelve a la copia anterior. Nunca frena el workflow.

Variables: HSN_SOURCE, PROYECTOS_LOTE (expedientes abiertos a revisar por corrida; 100 por defecto),
VENTANA_DIAS (30 por defecto), FECHA_DESDE (DD/MM/AAAA, para recuperar un período más largo).
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
PROYECTOS = os.path.join(DATA, "proyectos.json")


def sembrar(archivo):
    destino = os.path.join(DATA, archivo)
    if os.path.exists(destino):
        return True
    origen = os.path.join(SOURCE, "data", archivo)
    if not os.path.exists(origen):
        print("AVISO  No hay %s propio ni en la fuente." % archivo)
        return False
    os.makedirs(DATA, exist_ok=True)
    shutil.copyfile(origen, destino)
    print("Sembrado data/%s con el de la fuente." % archivo)
    return True


def cantidad(ruta):
    try:
        return len(json.load(open(ruta, encoding="utf-8")))
    except Exception:
        return None


def main():
    if not sembrar("proyectos.json"):
        return 0
    sembrar("acuerdos.json")
    sembrar("senadores.json")  # sólo si el padrón propio no se pudo armar antes
    antes = cantidad(PROYECTOS)
    copia = PROYECTOS + ".previo"
    shutil.copyfile(PROYECTOS, copia)
    env = dict(os.environ)
    env.setdefault("LOTE_REVISION", os.environ.get("PROYECTOS_LOTE", "100"))
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "scraper_proyectos.py")], cwd=ROOT, env=env)
        if r.returncode != 0:
            print("AVISO  scraper_proyectos.py terminó con código %d. Se conserva lo anterior." % r.returncode)
            shutil.copyfile(copia, PROYECTOS)
    except Exception as e:
        print("AVISO  No se pudo correr scraper_proyectos.py (%s). Se conserva lo anterior." % e)
        shutil.copyfile(copia, PROYECTOS)
    despues = cantidad(PROYECTOS)
    if antes and (despues is None or despues < antes * 0.98):
        print("AVISO  Los proyectos bajaron de %s a %s: se vuelve a la copia anterior." % (antes, despues))
        shutil.copyfile(copia, PROYECTOS)
        despues = antes
    try:
        os.remove(copia)
    except OSError:
        pass
    print("Proyectos propios: %s antes, %s después." % (antes, despues))
    return 0


if __name__ == "__main__":
    sys.exit(main())
