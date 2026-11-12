#!/usr/bin/env python3
"""sembrar_fijos.py — Copia UNA SOLA VEZ los archivos que no cambian (fotos de senadores, tipografía
Poppins, índice de fotos) desde el repo del sistema legislativo, si este repo todavía no los tiene.
Después de la primera corrida el repo ya los guarda y no vuelve a mirar la fuente.
Nunca frena el workflow."""
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
SOURCE = os.environ.get("HSN_SOURCE", os.path.join(ROOT, "source"))


def main():
    os.makedirs(DATA, exist_ok=True)
    for archivo in ("fotos_senadores.json", "fonts_poppins.json"):
        destino, origen = os.path.join(DATA, archivo), os.path.join(SOURCE, "data", archivo)
        if not os.path.exists(destino) and os.path.exists(origen):
            shutil.copyfile(origen, destino)
            print("Sembrado data/%s." % archivo)
    am, am_auto = os.path.join(DATA, "ayuda_memoria.json"), os.path.join(DATA, "ayuda_memoria_auto.json")
    if not os.path.exists(am) and os.path.exists(am_auto):
        shutil.copyfile(am_auto, am)
        print("data/ayuda_memoria.json creada a partir de la Ayuda Memoria armada del Senado.")
    fotos_o, fotos_d = os.path.join(SOURCE, "data", "fotos"), os.path.join(DATA, "fotos")
    if os.path.isdir(fotos_o) and not os.path.isdir(fotos_d):
        shutil.copytree(fotos_o, fotos_d)
        print("Sembradas las fotos de senadores (%d)." % len(os.listdir(fotos_d)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
