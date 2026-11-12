"""Genera la Ayuda Memoria desde los PDF de las Órdenes del Día (sin planilla manual).

Hoy data/ayuda_memoria.json sale de AYUDA_MEMORIA_2026.xlsx, que se completa a mano
(texto del dictamen, firmantes, comisión cabecera) más un export del sitio del Senado
(fecha). Todo eso figura en el PDF de cada OD; este script lo lee de ahí.

Usos (desde la raíz del repo):

  # Leer los PDF de una carpeta y generar el JSON (NO pisa data/ayuda_memoria.json):
  py scripts/generar_ayuda_memoria.py --pdfs pdfs_od

  # Además, compararlo con lo que hay hoy cargado a mano:
  py scripts/generar_ayuda_memoria.py --pdfs pdfs_od --comparar data/ayuda_memoria.json

  # Bajar del sitio del Senado los PDF de ciertas OD (usa data/od.json) y generar:
  py scripts/generar_ayuda_memoria.py --pdfs pdfs_od --descargar 371 366 113

  # Bajar y generar las mismas OD que hoy figuran en la Ayuda Memoria cargada a mano
  # (para comparar todas contra la planilla):
  py scripts/generar_ayuda_memoria.py --pdfs pdfs_od --numeros-de data/ayuda_memoria.json --comparar data/ayuda_memoria.json

Salida por defecto: data/ayuda_memoria_auto.json, con el mismo formato que ayuda_memoria.json
(más "disidencias" cuando la OD las tiene). Qué OD entran en la Ayuda Memoria lo decide
la carpeta de PDF: este script no decide cuáles ya se trataron.
"""
import argparse
import glob
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extraer_od import leer_od  # noqa: E402
from parse_ayuda_memoria import (  # noqa: E402
    CATEGORIA_MAP, ORIGEN_MAP, OVERRIDES_AUTOR, _extraer_autor,
)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
HEADERS = {  # mismo criterio que el resto de los scrapers: User-Agent propio y honesto
    "User-Agent": "HSN-SistemaLegislativo/1.0 (+https://github.com/bonifaciomariano/hsn-sistema-legislativo)",
}
MINUSCULAS = {"y", "e", "de", "del", "la", "las", "los", "el", "en", "o", "para"}


def cargar(nombre, defecto):
    ruta = os.path.join(DATA, nombre)
    if not os.path.exists(ruta):
        return defecto
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def titulo_comision(texto):
    """'SISTEMAS, MEDIOS DE COMUNICACIÓN Y LIBERTAD DE EXPRESIÓN' -> 'Sistemas, Medios de Comunicación y Libertad de Expresión'"""
    palabras = (texto or "").lower().split()
    return " ".join(p if (i and p in MINUSCULAS) else p[:1].upper() + p[1:] for i, p in enumerate(palabras))


def lista_comisiones(texto):
    """'COMISIÓN DE A, DE B Y DE C' -> ['A', 'B', 'C']"""
    t = re.sub(r"^COMISI[ÓO]N(?:ES)?\s+DE\s+", "", texto or "", flags=re.I)
    # solo se corta en «, DE» y «Y DE»: hay comisiones con coma en el nombre
    return [x.strip() for x in re.split(r",\s+DE\s+|\s+Y\s+DE\s+", t, flags=re.I) if x.strip()]


def sin_repetidos(lista):
    vistos, out = set(), []
    for x in lista:
        if x not in vistos:
            vistos.add(x)
            out.append(x)
    return out


RE_GERUNDIO = re.compile(r"\s+[a-záéíóúñ]{4,}(?:ando|iendo)\b.*$")


def limpiar_autor(autor):
    """Si el PDF no trae coma después del autor («senador Lewandowski expresando…»),
    la regla de Mariano se lleva el resto de la frase: se corta en el primer gerundio en minúscula."""
    if autor and len(autor) > 30:
        return RE_GERUNDIO.sub("", autor).strip()
    return autor


def codigo_exp(e):
    return f"{e['origen']}-{e['nro']}/{str(e['anio'])[-2:]}"


def nombre_pdf(od):
    return f"{od['anio_od']}_{od['nro_od']:04d}_{od['tipo_od']}.pdf"


def descargar(numeros, carpeta, anio):
    """Baja a `carpeta` los PDF de las OD pedidas (normal y anexo) que todavía no estén."""
    import requests
    os.makedirs(carpeta, exist_ok=True)
    pedidas = [o for o in cargar("od.json", []) if o["anio_od"] == anio and o["nro_od"] in numeros and o.get("url_pdf")]
    if not pedidas:
        print("AVISO: ninguna de esas OD está en data/od.json con enlace al PDF")
    nuevas = [od for od in pedidas if not os.path.exists(os.path.join(carpeta, nombre_pdf(od)))]
    print(f"{len(pedidas)} PDF pedidos, {len(pedidas) - len(nuevas)} ya estaban, se bajan {len(nuevas)}")
    fallidas = []
    for i, od in enumerate(nuevas, 1):
        destino = os.path.join(carpeta, nombre_pdf(od))
        try:
            r = requests.get(od["url_pdf"], headers=HEADERS, timeout=60)
            r.raise_for_status()
        except Exception as err:  # una que falla no frena a las demás
            fallidas.append((nombre_pdf(od), str(err)[:80]))
            continue
        with open(destino, "wb") as f:
            f.write(r.content)
        print(f"  [{i}/{len(nuevas)}] bajado {os.path.basename(destino)} ({len(r.content) // 1024} KB)")
        time.sleep(1)
    for nombre, motivo in fallidas:
        print(f"AVISO: no se pudo bajar {nombre}: {motivo}")


def armar_fila(r, od_idx, proy_idx):
    avisos = list(r["avisos"])
    tipo_od = "A" if r["tipo"] == "ANEXO" else "N"
    od = od_idx.get((r["numero"], r["periodo"], tipo_od))
    if not od:
        avisos.append("no está en data/od.json (sin enlace ni expedientes con url)")
    exps = (od or {}).get("expedientes") or []
    primero = exps[0] if exps else None

    origen = ORIGEN_MAP.get(primero["origen"], primero["origen"].title()) if primero else ""
    categoria = CATEGORIA_MAP.get(primero["tipo"], "Proyecto de Ley") if primero else "Proyecto de Ley"

    cabecera = titulo_comision(r["comision"]) or None
    giros = []
    if primero:
        p = proy_idx.get((primero["origen"], primero["nro"], primero["anio"]))
        giros = (p or {}).get("comisiones") or []
        if not p:
            avisos.append("expediente no encontrado en data/proyectos.json (sin giros)")
    if not giros:  # expediente sin giros cargados (p. ej. de años anteriores): usar las comisiones que nombra el PDF
        giros = ["DE " + c.upper() for c in lista_comisiones(r.get("comisiones_texto"))]
        avisos = [a for a in avisos if not a.startswith("expediente no encontrado")]
    comisiones = sin_repetidos(([cabecera] if cabecera else []) + [g for g in giros if g])

    fila = {
        "numero": str(r["numero"]),
        "periodo": r["periodo"],
        "origen": origen,
        "categoria": categoria,
        "autor": OVERRIDES_AUTOR.get((r["numero"], r["periodo"])) or limpiar_autor(_extraer_autor(r["sumario"])),
        "descripcion": r["sumario"],
        "expedientes": [{"codigo": codigo_exp(e), "url": e.get("url")} for e in exps],
        "comisionCabecera": cabecera,
        "fechaDictamen": r["fecha_dictamen"] if r["tipo"] == "ANEXO" else r["fecha_od"],
        "odLink": (od or {}).get("url_pdf"),
        "comisiones": comisiones,
        "tipoOD": r["tipo"],
        "firmantesMayoria": r["firmantes"],
    }
    if r["disidencias"]:
        fila["disidencias"] = r["disidencias"]
    return fila, avisos


def norm(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def clave(s):
    """Para comparar sin que importen mayúsculas, tildes ni las palabras «de/del» (en el Excel varían)."""
    t = unicodedata.normalize("NFD", norm(s).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return " ".join(w for w in t.replace(",", " ,").split() if w not in ("de", "del"))


def apellido(x):
    return clave(norm(x).split()[-1]) if norm(x) else ""


def apellidos(lista):
    return [apellido(x) for x in lista]


def donde_difiere(a, b, ancho=35):
    """Muestra el tramo donde dos textos empiezan a ser distintos."""
    a, b = norm(a), norm(b)
    k = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
    d = max(0, k - 20)
    return f"en el carácter {k}: automático=…{a[d:k + ancho]!r} | a mano=…{b[d:k + ancho]!r} (largos {len(a)} y {len(b)})"


def comparar(filas, ruta_ref):
    ref = json.load(open(ruta_ref, encoding="utf-8"))
    idx = {(f["numero"], f["periodo"], f["tipoOD"]): f for f in ref}
    print("\n=== Comparación con", ruta_ref, "(solo se detallan las que tienen diferencias)")
    iguales, sin_ref, por_campo = [], [], Counter()
    for f in filas:
        r = idx.get((f["numero"], f["periodo"], f["tipoOD"]))
        etiqueta = f"OD {f['numero']}/{f['periodo']} {f['tipoOD']}"
        if not r:
            sin_ref.append(etiqueta)
            continue
        dif = []
        for campo in ("origen", "categoria", "fechaDictamen", "odLink"):
            a, b = norm(f[campo]), norm(r.get(campo))
            if a != b:
                por_campo[campo] += 1
                dif.append(f"{campo}: automático={a[:90]!r} | a mano={b[:90]!r}")
        # autor y cabecera: no cuentan mayúsculas, tildes ni «de»
        for campo in ("autor", "comisionCabecera"):
            a, b = norm(f[campo]), norm(r.get(campo))
            if clave(a) != clave(b):
                por_campo[campo] += 1
                dif.append(f"{campo}: automático={a[:90]!r} | a mano={b[:90]!r}")
        a, b = norm(f["descripcion"]), norm(r.get("descripcion"))
        if a != b:
            por_campo["descripcion"] += 1
            dif.append("descripcion " + ("(solo mayúsculas/tildes) " if clave(a) == clave(b) else "") + donde_difiere(a, b))
        ea, em = [e["codigo"] for e in f["expedientes"]], [e["codigo"] for e in r["expedientes"]]
        if ea != em:
            por_campo["expedientes"] += 1
            dif.append(f"expedientes: automático={ea} | a mano={em}")
        if [clave(c) for c in f["comisiones"]] != [clave(c) for c in r["comisiones"]]:
            por_campo["comisiones"] += 1
            dif.append(f"comisiones: automático={f['comisiones']} | a mano={r['comisiones']}")
        fa, fm = f["firmantesMayoria"], r["firmantesMayoria"]
        if apellidos(fa) != apellidos(fm):
            extra = [n for d in f.get("disidencias", []) for n in d["firmantes"]]
            if apellidos(fa + extra) == apellidos(fm):
                por_campo["firmantes (disidentes)"] += 1
                dif.append(f"firmantes: a mano incluye {len(extra)} en disidencia dentro de la lista")
            else:
                por_campo["firmantes"] += 1
                solo_a = list((Counter(apellidos(fa)) - Counter(apellidos(fm))).elements())
                solo_m = list((Counter(apellidos(fm)) - Counter(apellidos(fa))).elements())
                dif.append(f"firmantes: automático={len(fa)} | a mano={len(fm)} -> solo en automático: {solo_a} | solo a mano: {solo_m}")
        elif fa != fm:
            dif.append("firmantes: mismas personas, distinto formato del nombre (a mano: " + ", ".join(fm[:2]) + "…)")
        if not dif:
            iguales.append(f"{f['numero']}{' A' if f['tipoOD'] == 'ANEXO' else ''}")
            continue
        print(f"- {etiqueta}:")
        for d in dif:
            print("    ·", d)
    print(f"\nRESUMEN: {len(iguales)} de {len(filas)} iguales en todo a lo cargado a mano; "
          f"{len(filas) - len(iguales) - len(sin_ref)} con diferencias; {len(sin_ref)} que no estaban en la planilla.")
    if por_campo:
        print("Diferencias por campo:", ", ".join(f"{k}: {v}" for k, v in por_campo.most_common()))
    if iguales:
        print("Iguales:", ", ".join(iguales))
    if sin_ref:
        print("No estaban en la planilla:", ", ".join(sin_ref))


def leer_pdfs(rutas, od_idx, proy_idx):
    """Lee los PDF indicados y devuelve (filas, problemas). Una OD repetida (mismo PDF con otro nombre) se lee una vez."""
    filas, problemas, vistas = [], [], set()
    # primero los PDF con nombre «año_número_tipo.pdf» (los que baja este script)
    rutas = sorted(rutas, key=lambda x: (not re.match(r"\d{4}_\d{4}_[NA]\.pdf$", os.path.basename(x)), os.path.basename(x)))
    for ruta in rutas:
        try:
            r = leer_od(ruta)
            if r["numero"] is None or r["periodo"] is None:
                problemas.append((os.path.basename(ruta), "no se pudo leer el número o el año de la OD"))
                continue
            clave_od = (r["numero"], r["periodo"], r["tipo"])
            if clave_od in vistas:  # el mismo PDF guardado con otro nombre: se usa uno solo
                problemas.append((os.path.basename(ruta), "repetido (ya se leyó esa OD en otro archivo): se ignora"))
                continue
            vistas.add(clave_od)
            fila, avisos = armar_fila(r, od_idx, proy_idx)
        except Exception as err:  # una OD rara no frena a las demás
            problemas.append((os.path.basename(ruta), f"error: {err}"))
            continue
        filas.append(fila)
        for av in avisos:
            problemas.append((f"OD {fila['numero']} {fila['tipoOD']}", av))
    return filas, problemas


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdfs", required=True, help="carpeta con los PDF de las OD")
    ap.add_argument("--salida", default=os.path.join(DATA, "ayuda_memoria_auto.json"))
    ap.add_argument("--comparar", help="JSON a comparar (por ejemplo data/ayuda_memoria.json)")
    ap.add_argument("--descargar", nargs="+", type=int, metavar="NRO", help="números de OD a bajar del sitio antes de leer")
    ap.add_argument("--numeros-de", metavar="JSON", help="bajar las OD que figuran en ese archivo (por ejemplo data/ayuda_memoria.json)")
    ap.add_argument("--anio", type=int, default=2026)
    a = ap.parse_args()

    pedir = set(a.descargar or [])
    if a.numeros_de:
        with open(a.numeros_de, encoding="utf-8") as f:
            pedir |= {int(x["numero"]) for x in json.load(f) if x.get("periodo") == a.anio}
    if pedir:
        descargar(pedir, a.pdfs, a.anio)

    od_idx = {(o["nro_od"], o["anio_od"], o["tipo_od"]): o for o in cargar("od.json", [])}
    proy_idx = {(p["origen"], p["nro"], p["anio"]): p for p in cargar("proyectos.json", [])}

    filas, problemas = leer_pdfs(sorted(glob.glob(os.path.join(a.pdfs, "*.pdf"))), od_idx, proy_idx)
    filas.sort(key=lambda f: (f["periodo"], int(f["numero"])), reverse=True)
    with open(a.salida, "w", encoding="utf-8") as f:
        json.dump(filas, f, ensure_ascii=False, indent=2)
    print(f"{len(filas)} órdenes del día leídas -> {a.salida}")
    for donde, que in problemas:
        print(f"AVISO {donde}: {que}")
    if a.comparar:
        comparar(filas, a.comparar)


if __name__ == "__main__":
    main()
