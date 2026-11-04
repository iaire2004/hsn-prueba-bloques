#!/usr/bin/env python3
"""comisiones_senado.py — Comisiones, integrantes y cargos PROPIOS de este repo (data/comisiones.json).

MODO SOMBRA: las páginas siguen usando las comisiones del repo del sistema legislativo; esta copia
se arma directo del Senado (una consulta por comisión, con pausa) y el verificador la compara con
la de la fuente. Cuando coinciden de forma estable se puede pasar a usarla.

  1. Si data/comisiones.json no existe, se siembra con la de la fuente (HSN_SOURCE/data/comisiones.json).
  2. Se agrega "Banca de la Mujer" (ID 76), que el scraper de la fuente nunca leyó por no estar en su archivo.
  3. Se lee cada comisión del Senado y se actualizan integrantes y cargos (reusa scraper_comisiones.py,
     con sus resguardos: tabla inválida = se deja como estaba; más de 5 fallos = no se escribe nada).
  4. Si el Senado no responde, se conserva lo anterior y se avisa. Nunca frena el workflow.

Variables: COMISIONES_LOCAL (carpeta con HTML guardados para pruebas sin red), TEST=1 (no escribe).
"""
import json
import os
import sys

os.environ["ACTUALIZAR"] = "1"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scraper_comisiones as sc  # noqa: E402

ROOT = os.path.dirname(HERE)
SOURCE = os.environ.get("HSN_SOURCE", os.path.join(ROOT, "source"))
EXTRA = ["Banca de la Mujer"]


def main():
    if not os.path.exists(sc.COMISIONES_JSON):
        try:
            coms = json.load(open(os.path.join(SOURCE, "data", "comisiones.json"), encoding="utf-8"))
        except Exception as e:
            print("AVISO  Sin comisiones de la fuente para sembrar (%s)." % e)
            return 0
        os.makedirs(sc.DATA_DIR, exist_ok=True)
        json.dump(coms, open(sc.COMISIONES_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("Comisiones propias sembradas con las de la fuente (%d)." % len(coms))
    coms = json.load(open(sc.COMISIONES_JSON, encoding="utf-8"))
    nombres = {c["nombre"] for c in coms}
    for nom in EXTRA:
        if nom not in nombres:
            coms.append({"nombre": nom, "cupo": 0, "miembros": []})
            print("  + comisión agregada para leer: %s" % nom)
    json.dump(coms, open(sc.COMISIONES_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if not os.path.exists(sc.SENADORES_JSON):
        print("AVISO  No hay data/senadores.json propio: corré antes padron_senadores.py")
        return 0
    if os.getenv("TEST") == "1":
        sc.ACTUALIZAR = False
    try:
        sc.main()
    except SystemExit as e:
        print("AVISO  %s Se conserva lo anterior." % e)
    # una comisión agregada que nunca se pudo leer queda vacía: no se deja en el archivo
    coms = json.load(open(sc.COMISIONES_JSON, encoding="utf-8"))
    limpias = [c for c in coms if c.get("miembros") or c["nombre"] not in EXTRA]
    if len(limpias) != len(coms):
        json.dump(limpias, open(sc.COMISIONES_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("AVISO  Comisión sin integrantes leídos, no se guarda: %s" % ", ".join(c["nombre"] for c in coms if c not in limpias))
    return 0


if __name__ == "__main__":
    sys.exit(main())
