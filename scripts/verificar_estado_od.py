"""Mira en el sitio del Senado el ESTADO de cada Orden del Día (PENDIENTE, APROBADA, …).

El Senado lo muestra en la ficha de cada expediente, en la tabla «Órdenes del Día»:

    NÚMERO   DE FECHA     ESTADO      ANEXO
    241/26   05-08-2026   PENDIENTE   Sin Anexo

La idea a probar: la Ayuda Memoria = las OD cuyo estado es PENDIENTE.
Este script NO cambia nada de la Ayuda Memoria: solo consulta y compara.

Uso (desde la raíz del repo):

  # Ver cuántas fichas se consultarían, sin consultar nada:
  py scripts/verificar_estado_od.py --candidatas --solo-contar

  # Consultar las de la Ayuda Memoria cargada a mano + las que parecen pendientes (≈110 fichas):
  py scripts/verificar_estado_od.py --candidatas

  # Consultar OD puntuales:
  py scripts/verificar_estado_od.py --od 241 365 5

Guarda lo consultado en data/estado_od.json; si lo volvés a correr, no repite las que ya tiene
(agregá --refrescar para volver a consultarlas). Es amable con el sitio: User-Agent propio,
1 segundo de pausa entre fichas, y se detiene si el sitio empieza a rechazar los pedidos.
"""
import argparse
import json
import os
import re
import sys
import time

from bs4 import BeautifulSoup

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
HEADERS = {  # mismo criterio que el resto de los scrapers: User-Agent propio y honesto
    "User-Agent": "HSN-SistemaLegislativo/1.0 (+https://github.com/bonifaciomariano/hsn-sistema-legislativo)",
}
PAUSA = 1.0

# «365/26   03-09-2026   APROBADA   Sin Anexo»: número/año, fecha, estado (palabras en mayúscula), anexo
# (la fecha puede venir vacía: la OD 369 la tiene así en el sitio)
RE_FILA = re.compile(
    r"(\d{1,4})/(\d{2})\s+(?:(\d{2}-\d{2}-\d{4})\s+)?((?:[A-ZÁÉÍÓÚÜÑ]{2,}\s?)+)"
)


def cargar(nombre, defecto):
    ruta = os.path.join(DATA, nombre)
    if not os.path.exists(ruta):
        return defecto
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def ods_de_la_ficha(html):
    """Devuelve las filas de la tabla «Órdenes del Día» de la ficha de un expediente:
    [{'nro': 241, 'anio': 2026, 'fecha': '05-08-2026', 'estado': 'PENDIENTE'}, …]"""
    texto = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    texto = re.sub(r"\s+", " ", texto)
    i = texto.lower().rfind("órdenes del día número")
    if i < 0:
        m = re.search(r"[ÓO]rdenes del D[ií]a\s+N[ÚU]MERO\s+DE FECHA\s+ESTADO", texto, re.I)
        if not m:
            return []
        i = m.start()
    bloque = texto[i:]
    # el bloque llega hasta el pie de la página; se corta donde ya no hay filas
    filas = []
    for m in RE_FILA.finditer(bloque):
        filas.append({
            "nro": int(m.group(1)),
            "anio": 2000 + int(m.group(2)),
            "fecha": m.group(3) or None,
            "estado": m.group(4).strip(),
        })
    return filas


def rechazado(html):
    return "request rejected" in html.lower()[:2000]


def consultar(url, sesion):
    r = sesion.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    if rechazado(r.text):
        raise RuntimeError("el sitio rechazó el pedido (Request Rejected)")
    return ods_de_la_ficha(r.text)


def estado_de_od(o, anio, sesion, seguidas_malas=0):
    """Mira la ficha del/los expediente(s) de una OD y devuelve (estado, fecha, fichas_probadas, seguidas_malas).
    seguidas_malas cuenta pedidos fallidos seguidos: con 3 hay que parar."""
    n = o["nro_od"]
    estado, fecha, probadas = None, None, 0
    for e in o["expedientes"]:
        if not e.get("url"):
            continue
        probadas += 1
        try:
            filas = consultar(e["url"], sesion)
            seguidas_malas = 0
        except Exception as err:
            print(f"  OD {n}: ERROR {str(err)[:80]}")
            seguidas_malas += 1
            filas = None
        time.sleep(PAUSA)
        if seguidas_malas >= 3:
            break
        propias = [f for f in (filas or []) if f["nro"] == n and f["anio"] == anio]
        if propias:
            estado, fecha = propias[0]["estado"], propias[0]["fecha"]
            break
    return estado, fecha, probadas, seguidas_malas


def candidatas(ruta_ayuda):
    """OD 2026 a consultar: las de la Ayuda Memoria cargada a mano + las que, según los datos de Mariano
    (proyectos.json y sanciones.json), parecen pendientes."""
    od = [o for o in cargar("od.json", []) if o["anio_od"] == 2026 and o["tipo_od"] == "N"]
    nums = set()
    if ruta_ayuda and os.path.exists(ruta_ayuda):
        with open(ruta_ayuda, encoding="utf-8") as f:
            nums |= {int(x["numero"]) for x in json.load(f) if x.get("periodo") == 2026}
    P = {(p["origen"], p["nro"], p["anio"]): p for p in cargar("proyectos.json", [])}
    norm = lambda c: re.sub(r"\s", "", c).upper()
    tratados = {norm(s["expediente"]) for s in cargar("sanciones.json", []) if s.get("seccion") != "preferencia"}
    for o in od:
        ps = [P.get((e["origen"], e["nro"], e["anio"])) for e in o["expedientes"]]
        ps = [p for p in ps if p]
        cods = [f"{e['origen']}-{e['nro']}/{str(e['anio'])[-2:]}" for e in o["expedientes"]]
        if not any(p["archivado"] or p["sancionado"] for p in ps) and not any(norm(c) in tratados for c in cods):
            nums.add(o["nro_od"])
    return nums


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--od", nargs="+", type=int, metavar="NRO", help="números de OD (2026) a consultar")
    ap.add_argument("--candidatas", action="store_true", help="las de la Ayuda Memoria a mano + las que parecen pendientes")
    ap.add_argument("--ayuda", default=os.path.join(DATA, "ayuda_memoria_manual.json"),
                    help="Ayuda Memoria cargada a mano (para comparar)")
    ap.add_argument("--salida", default=os.path.join(DATA, "estado_od.json"))
    ap.add_argument("--refrescar", action="store_true", help="volver a consultar las que ya están guardadas")
    ap.add_argument("--solo-contar", action="store_true", help="no consulta nada: solo dice cuántas fichas serían")
    ap.add_argument("--anio", type=int, default=2026)
    a = ap.parse_args()

    pedidas = set(a.od or [])
    if a.candidatas:
        pedidas |= candidatas(a.ayuda)
    if not pedidas:
        sys.exit("Indicá --od NRO … o --candidatas")

    od_idx = {o["nro_od"]: o for o in cargar("od.json", []) if o["anio_od"] == a.anio and o["tipo_od"] == "N"}
    guardado = {}
    if os.path.exists(a.salida):
        with open(a.salida, encoding="utf-8") as f:
            guardado = json.load(f)
    por_hacer = sorted(n for n in pedidas if n in od_idx and (a.refrescar or not (guardado.get(str(n)) or {}).get("estado")))
    sin_datos = sorted(n for n in pedidas if n not in od_idx)
    print(f"{len(pedidas)} OD pedidas; {len(pedidas) - len(por_hacer) - len(sin_datos)} ya estaban guardadas; "
          f"se consultan {len(por_hacer)} fichas")
    if sin_datos:
        print("AVISO: no están en data/od.json:", sin_datos)
    if a.solo_contar:
        return

    import requests
    sesion = requests.Session()
    seguidas_malas = 0
    for i, n in enumerate(por_hacer, 1):
        estado, fecha, probadas, seguidas_malas = estado_de_od(od_idx[n], a.anio, sesion, seguidas_malas)
        if seguidas_malas >= 3:
            print("Se detiene: 3 pedidos seguidos fallaron. Probá más tarde.")
            break
        guardado[str(n)] = {"estado": estado, "fecha": fecha, "expedientes_probados": probadas}
        print(f"  [{i}/{len(por_hacer)}] OD {n}: {estado or 'NO SE PUDO LEER'}")
        with open(a.salida, "w", encoding="utf-8") as f:
            json.dump(guardado, f, ensure_ascii=False, indent=2)

    # ---- comparación con la Ayuda Memoria cargada a mano
    en_ayuda = set()
    if os.path.exists(a.ayuda):
        with open(a.ayuda, encoding="utf-8") as f:
            en_ayuda = {int(x["numero"]) for x in json.load(f) if x.get("periodo") == a.anio}
    consultadas = {int(k): v for k, v in guardado.items() if int(k) in pedidas}
    pend = {n for n, v in consultadas.items() if v["estado"] == "PENDIENTE"}
    sin_leer = sorted(n for n, v in consultadas.items() if not v["estado"])
    sobrantes = sorted(n for n in consultadas if n in en_ayuda and n not in pend and n not in sin_leer)
    faltantes = sorted(n for n in pend if n not in en_ayuda)
    estados = {}
    for v in consultadas.values():
        estados[v["estado"]] = estados.get(v["estado"], 0) + 1
    print("\n=== RESUMEN")
    print("Estados encontrados:", dict(sorted(estados.items(), key=lambda kv: -kv[1])))
    print(f"En la Ayuda Memoria y PENDIENTES: {len([n for n in consultadas if n in en_ayuda and n in pend])} de {len([n for n in consultadas if n in en_ayuda])} consultadas")
    print("En la Ayuda Memoria pero NO pendientes:", sobrantes or "ninguna")
    print("PENDIENTES que no están en la Ayuda Memoria:", faltantes or "ninguna")
    if sin_leer:
        print("No se pudo leer el estado de:", sin_leer)
    print("Guardado en", a.salida)


if __name__ == "__main__":
    main()
