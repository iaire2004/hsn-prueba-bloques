#!/usr/bin/env python3
"""padron_senadores.py — Padrón de senadores PROPIO de este repo (data/senadores.json).

Objetivo: no depender del padrón del repo del sistema legislativo. Cada corrida:
  1. Si data/senadores.json no existe, lo siembra con una copia del padrón de la fuente
     (HSN_SOURCE/data/senadores.json). Después nunca lo pisa con el de la fuente.
  2. Suma a nuestro padrón los senadores históricos que sólo estén en la fuente (no pisa nada).
  3. Lee el listado oficial por bloque (senado.gob.ar, una sola consulta) y actualiza
     vigencia y bloque (reusa el lector probado de scraper_senadores.py).
     Si el Senado no responde o la página cambió, se conserva el padrón anterior y se avisa.
  4. Completa provincias vacías: primero desde la fuente, luego desde data/provincias_manuales.json.
  5. Chequeos de seguridad (menos de 60 senadores / 8 bloques = no se toca nada).

generar_bloques.py usa este padrón si existe; si no, el de la fuente.

Variables: SENADORES_BLOQUES_URL / SENADORES_BLOQUES_HTML (pruebas sin red) / TEST=1 (no escribe).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scraper_senadores as ss  # noqa: E402

ROOT = os.path.dirname(HERE)
SOURCE = os.environ.get("HSN_SOURCE", os.path.join(ROOT, "source"))
PROPIO = ss.SENADORES_JSON
MANUALES = os.path.join(ss.DATA_DIR, "provincias_manuales.json")
TEST = os.getenv("TEST", "") == "1"


def cargar(ruta, defecto):
    try:
        return json.load(open(ruta, encoding="utf-8"))
    except Exception:
        return defecto


def main():
    fuente = cargar(os.path.join(SOURCE, "data", "senadores.json"), {})
    propio = cargar(PROPIO, None)
    if propio is None:
        propio = {k: dict(v) for k, v in fuente.items()}
        print("Padrón propio sembrado con el de la fuente (%d registros)." % len(propio))
    por_norm = {ss.normalizar_nombre(k): k for k in propio}
    for k, v in fuente.items():
        if ss.normalizar_nombre(k) not in por_norm:
            propio[k] = dict(v)
            print("  + histórico tomado de la fuente: %s" % k)

    cambios = []
    try:
        web, por_bloque = ss.parsear(ss.obtener_html())
        # actualizar_padron lee/escribe sobre ss.SENADORES_JSON: lo dejamos listo antes de llamarlo
        if not TEST:
            os.makedirs(ss.DATA_DIR, exist_ok=True)
            json.dump(propio, open(PROPIO, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        else:
            json.dump(propio, open(PROPIO + ".tmp", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            ss.SENADORES_JSON = PROPIO + ".tmp"
        propio, cambios = ss.actualizar_padron(web, por_bloque)
    except SystemExit as e:
        print("AVISO  Senado no utilizable (%s). Se conserva el padrón anterior." % e)
    except Exception as e:
        print("AVISO  No se pudo leer el listado del Senado (%s). Se conserva el padrón anterior." % e)

    # Provincias vacías: fuente -> manuales
    manuales = {ss.normalizar_nombre(k): v for k, v in cargar(MANUALES, {}).items() if not k.startswith("_")}
    f_norm = {ss.normalizar_nombre(k): v for k, v in fuente.items()}
    for k, v in propio.items():
        if not v.get("provincia"):
            n = ss.normalizar_nombre(k)
            p = (f_norm.get(n) or {}).get("provincia") or manuales.get(n)
            if p:
                v["provincia"] = p
                cambios.append("PROVINCIA: %s -> %s" % (k, p))
    for c in cambios:
        print("  " + c)
    print("Padrón propio: %d registros, %d vigentes." % (len(propio), sum(1 for v in propio.values() if v.get("vigente"))))
    sin = [k for k, v in propio.items() if v.get("vigente") and not v.get("provincia")]
    for k in sin:
        print("AVISO  vigente sin provincia: %s (agregarla en data/provincias_manuales.json)" % k)
    if TEST:
        print("TEST=1: no se escribe.")
        return 0
    json.dump(propio, open(PROPIO, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
