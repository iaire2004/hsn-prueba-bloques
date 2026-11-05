#!/usr/bin/env python3
"""agenda_od_senado.py — Agenda de comisiones y Órdenes del Día PROPIAS de este repo.

MODO SOMBRA: las páginas siguen usando agenda y OD del repo del sistema legislativo; estas copias
se arman directo del Senado y el verificador las compara con las de la fuente.

Para cada pieza (agenda: boletines de reuniones; od: órdenes del día):
  1. Si el archivo propio no existe, se siembra con el de la fuente (son incrementales: sin esa base
     volverían a bajar todo el historial).
  2. Se corre el scraper (copia de los de la fuente). Si el Senado no responde, queda lo anterior.
  3. Nunca frena el workflow: cualquier error se avisa y se sigue.

Uso: python scripts/agenda_od_senado.py [agenda|od]   (sin argumento corre las dos)
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
SOURCE = os.environ.get("HSN_SOURCE", os.path.join(ROOT, "source"))

PIEZAS = {
    "agenda": {"script": "scraper_agenda.py", "archivos": ["agenda.json", "boletines_procesados.json"]},
    "od": {"script": "scraper_od.py", "archivos": ["od.json"]},
}


def sembrar(archivo):
    destino = os.path.join(DATA, archivo)
    if os.path.exists(destino):
        return True
    origen = os.path.join(SOURCE, "data", archivo)
    if not os.path.exists(origen):
        print("AVISO  No hay %s propio ni en la fuente: se parte de cero (puede tardar)." % archivo)
        return False
    os.makedirs(DATA, exist_ok=True)
    shutil.copyfile(origen, destino)
    print("Sembrado data/%s con el de la fuente." % archivo)
    return True


def correr(nombre):
    p = PIEZAS[nombre]
    print("== %s ==" % nombre)
    for a in p["archivos"]:
        sembrar(a)
    # la agenda usa data/comisiones.json para resolver nombres: si no hay propio, el de la fuente
    if nombre == "agenda":
        sembrar("comisiones.json")
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, p["script"])], cwd=ROOT)
        if r.returncode != 0:
            print("AVISO  %s terminó con código %d. Se conserva lo anterior." % (p["script"], r.returncode))
    except Exception as e:
        print("AVISO  No se pudo correr %s (%s). Se conserva lo anterior." % (p["script"], e))


def main():
    pedidas = sys.argv[1:] or list(PIEZAS)
    for n in pedidas:
        if n not in PIEZAS:
            print("Pieza desconocida: %s (usar agenda u od)" % n)
            continue
        correr(n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
