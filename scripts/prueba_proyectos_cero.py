#!/usr/bin/env python3
"""prueba_proyectos_cero.py — ¿Los proyectos de 2026 se reconstruyen SOLO desde el Senado?

Corre scraper_proyectos.py en una carpeta temporal con data/ vacía (sólo el padrón propio, que se usa
para asignar bloques y provincias), buscando desde el 01/01/2026 y SIN revisar abiertos. Compara lo
que baja contra data/proyectos.json. NO modifica data/. Nunca frena el workflow.

Variables: PRUEBA_DESDE (DD/MM/AAAA, 01/01/2026 por defecto).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
DESDE = os.environ.get("PRUEBA_DESDE", "01/01/2026")
ANIO = DESDE.split("/")[-1]


def clave(p):
    return (str(p.get("origen") or "").strip(), str(p.get("nro")), str(p.get("anio")), str(p.get("tipo")).strip())


def desde_iso():
    d, m, a = DESDE.split("/")
    return "%s-%s-%s" % (a, m, d)


def en_periodo(p):
    f = str(p.get("fecha") or "")
    if len(f) >= 10 and f[4] == "-":
        return f[:10] >= desde_iso()
    if len(f) >= 10 and f[2] == "/":
        return f[6:10] + "-" + f[3:5] + "-" + f[:2] >= desde_iso()
    return str(p.get("anio")) == ANIO


def ventanas():
    """Tramos de ~30 días desde DESDE hasta hoy (la búsqueda del Senado se hace por fecha de Mesa de Entradas)."""
    d, m, a = (int(x) for x in DESDE.split("/"))
    ini = datetime(a, m, d)
    hoy = datetime.now()
    out = []
    while ini <= hoy:
        fin = min(ini + timedelta(days=29), hoy)
        out.append((ini, fin))
        ini = fin + timedelta(days=1)
    return out


def main():
    tmp = tempfile.mkdtemp(prefix="cero_proy_")
    os.makedirs(os.path.join(tmp, "scripts"))
    os.makedirs(os.path.join(tmp, "data"))
    for f in ("scraper_proyectos.py", "autoria_caratula.py"):
        shutil.copy(os.path.join(HERE, f), os.path.join(tmp, "scripts", f))
    # copia de trabajo del scraper: permite fijar también el FIN de la ventana (FECHA_HASTA)
    ruta = os.path.join(tmp, "scripts", "scraper_proyectos.py")
    codigo = open(ruta, encoding="utf-8").read()
    marca = "    hoy = datetime.now()\n    if FECHA_DESDE_FIJA:"
    if marca in codigo:
        codigo = codigo.replace(
            marca,
            "    hoy = datetime.now()\n    if os.getenv('FECHA_HASTA'):\n"
            "        hoy = datetime.strptime(os.getenv('FECHA_HASTA'), '%d/%m/%Y')\n    if FECHA_DESDE_FIJA:", 1)
        open(ruta, "w", encoding="utf-8").write(codigo)
    else:
        print("AVISO  No se pudo preparar la ventana por tramos; se busca todo de una vez.")
    sen = os.path.join(DATA, "senadores.json")
    if os.path.exists(sen):
        shutil.copy(sen, os.path.join(tmp, "data", "senadores.json"))
    print("Prueba desde cero de proyectos: buscando desde %s por tramos de 30 días (puede tardar bastante)..." % DESDE)
    rc = 0
    for ini, fin in ventanas():
        env = dict(os.environ, FECHA_DESDE=ini.strftime("%d/%m/%Y"), FECHA_HASTA=fin.strftime("%d/%m/%Y"),
                   LOTE_REVISION="0")
        log = os.path.join(tmp, "corrida.log")
        try:
            with open(log, "w") as fh:
                r = subprocess.run([sys.executable, ruta], cwd=tmp, env=env, stdout=fh, stderr=subprocess.STDOUT)
            rc = r.returncode or rc
        except Exception as e:
            print("AVISO  No se pudo correr el tramo %s: %s" % (ini.strftime("%d/%m/%Y"), e))
            rc = 1
            continue
        lineas = open(log, encoding="utf-8", errors="replace").read().splitlines()
        clave_l = [l for l in lineas if re.search(r"ERROR|Error|WARNING|expedientes en total|nuevos a procesar|TOTAL en", l)]
        print("--- tramo %s a %s ---" % (ini.strftime("%d/%m/%Y"), fin.strftime("%d/%m/%Y")))
        for l in clave_l[-8:]:
            print("   ", l[:220])
        time.sleep(2)
    try:
        cero = json.load(open(os.path.join(tmp, "data", "proyectos.json"), encoding="utf-8"))
        propios = json.load(open(os.path.join(DATA, "proyectos.json"), encoding="utf-8"))
    except Exception:
        cero, propios = [], []
    if rc != 0 or not cero:
        print("No se concluye nada: el scraper terminó con código %s y bajó %d proyectos." % (rc, len(cero)))
        return 0
    A = {clave(p): p for p in cero}
    B = {clave(p): p for p in propios if en_periodo(p)}
    comunes = set(A) & set(B)
    sol_a, sol_b = sorted(set(A) - set(B)), sorted(set(B) - set(A))
    print("\n=== PROYECTOS desde %s ===" % DESDE)
    print("Desde cero (sólo Senado): %d | En data/proyectos.json: %d | En ambos: %d" % (len(A), len(B), len(comunes)))
    print("Sólo desde cero (le faltan a data): %d" % len(sol_a))
    for k in sol_a[:15]:
        print("   ", k)
    print("Sólo en data (no aparecen desde cero): %d" % len(sol_b))
    for k in sol_b[:15]:
        print("   ", k, "fecha:", B[k].get("fecha"))
    for campo in ("fecha", "extracto", "autores", "coautores", "bloques", "provincias", "tipo_label"):
        difs = [k for k in comunes if A[k].get(campo) != B[k].get(campo)]
        if difs:
            print("Diferencias en '%s': %d" % (campo, len(difs)))
            for k in sorted(difs)[:4]:
                print("   ", k, "| cero:", str(A[k].get(campo))[:70], "| data:", str(B[k].get(campo))[:70])
    if not (sol_a or sol_b):
        print("Coinciden los mismos expedientes en el período.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
