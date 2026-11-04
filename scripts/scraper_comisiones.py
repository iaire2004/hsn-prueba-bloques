#!/usr/bin/env python3
"""
scraper_comisiones.py — Integrantes y cargos de cada comisión, desde el Senado.

Lee la página de cada comisión (senado.gob.ar/parlamentario/comisiones/info/<ID>), tabla
"Integrantes" (nombre, cargo, bloque, distrito), y la compara con data/comisiones.json.

Por defecto es MODO COMPARACIÓN: imprime las diferencias y no escribe nada.
Con ACTUALIZAR=1 corrige data/comisiones.json:
  - altas/bajas de integrantes según el Senado;
  - cargo (Presidente / Vicepresidente / Secretario; vocal = "");
  - bloque, respetando la grafía del padrón (data/senadores.json);
  - cupo = cantidad de lugares que informa el Senado (incluye "SENADOR VACANTE").
Los integrantes ya existentes conservan su nombre tal como están en comisiones.json.

Resguardos: si una comisión viene sin tabla o con menos de 5 filas, se deja como está y
se informa; si fallan más de 5 comisiones, no se escribe nada. Copia previa en
data/comisiones_backup.json. Una consulta por comisión, con pausa entre consultas.

Variables de entorno:
    ACTUALIZAR            "1" = escribir comisiones.json
    COMISIONES_LOCAL      carpeta con HTML guardados "<ID>.html" (pruebas sin red)
    TEST                  "1" = nunca escribe
"""
import json
import os
import re
import sys
import time
import unicodedata

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
COMISIONES_JSON = os.path.join(DATA_DIR, "comisiones.json")
SENADORES_JSON = os.path.join(DATA_DIR, "senadores.json")
BACKUP = os.path.join(DATA_DIR, "comisiones_backup.json")
URL = "https://www.senado.gob.ar/parlamentario/comisiones/info/{id}"
UA = ("HSN-Sistema-Legislativo/1.0 (herramienta interna de la Prosecretaria Parlamentaria; "
      "1 consulta por comision por corrida)")
ACTUALIZAR = os.getenv("ACTUALIZAR", "") == "1"
TEST = os.getenv("TEST", "") == "1"
LOCAL = os.getenv("COMISIONES_LOCAL", "").strip()

# ID de cada comisión permanente (unicameral) en senado.gob.ar
IDS = {
    "Banca de la Mujer": 76, "De Acuerdos": 71, "De Agricultura, Ganadería y Pesca": 62,
    "De Ambiente y Desarrollo Sustentable": 69, "De Asuntos Administrativos y Municipales": 55,
    "De Asuntos Constitucionales": 50, "De Ciencia y Tecnología": 74,
    "De Coparticipación Federal de Impuestos": 72, "De Defensa Nacional": 56, "De Deporte": 77,
    "De Derechos y Garantías": 64, "De Economía Nacional e Inversión": 58,
    "De Economías Regionales, Economía Social, Micro, Pequeña y Mediana Empresa": 60,
    "De Educación y Cultura": 75, "De Industria y Comercio": 59,
    "De Infraestructura, Vivienda y Transporte": 67, "De Justicia y Asuntos Penales": 52,
    "De Legislación General": 53, "De Minería, Energía y Combustibles": 65,
    "De Población y Desarrollo Humano": 70, "De Presupuesto y Hacienda": 54,
    "De Relaciones Exteriores y Culto": 51, "De Salud": 78,
    "De Seguridad Interior y Narcotráfico": 57,
    "De Sistemas, Medios de Comunicación y Libertad de Expresión": 68,
    "De Trabajo y Previsión Social": 61, "De Turismo": 73,
}
CARGOS = {"PRESIDENTE": "Presidente", "PRESIDENTA": "Presidente",
          "VICEPRESIDENTE": "Vicepresidente", "VICEPRESIDENTA": "Vicepresidente",
          "SECRETARIO": "Secretario", "SECRETARIA": "Secretario"}


def sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")


def clave_nombre(n):
    """Clave independiente del orden: conjunto de palabras sin tildes/comas, en mayúsculas."""
    n = sin_tildes((n or "").upper()).replace(",", " ")
    return " ".join(sorted(n.split()))


def clave_bloque(b):
    b = re.sub(r"\bPOR\b", " ", sin_tildes((b or "").upper()))
    return " ".join(b.split())


def formato_nombre(web_nombre):
    """'ENRIQUE MARTÍN  GOERLING LARA' (nombre, DOS espacios, apellido) -> 'GOERLING LARA, Enrique Martín'."""
    partes = [p.strip() for p in re.split(r"\s{2,}", web_nombre.strip()) if p.strip()]
    if len(partes) >= 2:
        nom, ape = partes[0], " ".join(partes[1:])
        return f"{ape.upper()}, {nom.title()}"
    return web_nombre.strip().upper()


def formato_nombre_padron(k):
    """'REJAL, JESÚS FERNANDO' (clave del padrón) -> 'REJAL, Jesús Fernando'."""
    a, _, b = k.partition(",")
    return f"{a.strip()}, {b.strip().title()}" if b else k


def obtener_html(cid):
    if LOCAL:
        p = os.path.join(LOCAL, f"{cid}.html")
        return open(p, encoding="utf-8", errors="replace").read() if os.path.exists(p) else None
    import requests
    r = requests.get(URL.format(id=cid), headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    return r.text


def parsear(html):
    """Devuelve lista de dicts {nombre, cargo, bloque, vacante} o None si no hay tabla."""
    from bs4 import BeautifulSoup
    s = BeautifulSoup(html, "html.parser")
    for t in s.find_all("table"):
        enc = [c.get_text(" ", strip=True).lower() for c in t.find_all("tr")[0].find_all(["th", "td"])] if t.find("tr") else []
        if "cargo" in enc and any(e.startswith("nombre") for e in enc) and "bloque" in enc:
            i_n = next(i for i, e in enumerate(enc) if e.startswith("nombre"))
            i_c, i_b = enc.index("cargo"), enc.index("bloque")
            out = []
            for tr in t.find_all("tr")[1:]:
                td = tr.find_all("td")
                if len(td) <= max(i_n, i_c, i_b):
                    continue
                # el nombre real lleva dos espacios entre nombre y apellido: no normalizar
                nombre = td[i_n].get_text(" ", strip=False).replace("\xa0", " ").strip()
                nombre = re.sub(r"[\r\n\t]+", " ", nombre)
                vac = "VACANTE" in nombre.upper()
                out.append({"nombre": nombre, "vacante": vac,
                            "cargo": td[i_c].get_text(" ", strip=True).upper(),
                            "bloque": td[i_b].get_text(" ", strip=True)})
            return out
    return None


def main():
    coms = json.load(open(COMISIONES_JSON, encoding="utf-8"))
    padron = json.load(open(SENADORES_JSON, encoding="utf-8")) if os.path.exists(SENADORES_JSON) else {}
    por_clave = {clave_nombre(k): (k, v) for k, v in padron.items()}
    canon = {}
    for v in padron.values():
        canon.setdefault(clave_bloque(v.get("bloque", "")), v.get("bloque", ""))

    nuevas, informe, fallos = [], [], []
    for c in coms:
        cid = IDS.get(c["nombre"])
        if cid is None:
            informe.append(f"(sin ID conocido, no se toca) {c['nombre']}")
            nuevas.append(c)
            continue
        try:
            html = obtener_html(cid)
        except Exception as e:                                  # red, bloqueo del sitio, etc.
            html = None
            fallos.append(f"{c['nombre']}: {e}")
        filas = parsear(html) if html else None
        if not filas or len(filas) < 5:
            if html is not None or LOCAL == "":
                fallos.append(f"{c['nombre']}: sin tabla de integrantes válida") if html else None
            nuevas.append(c)
            if not LOCAL:
                time.sleep(1.5)
            continue

        viejos = {clave_nombre(m["nombre"]): m for m in c["miembros"]}
        web_keys = [clave_nombre(f["nombre"]) for f in filas if not f["vacante"]]
        # un nombre incompleto en comisiones.json ('REJAL, Fernando') se asocia al nombre
        # completo del Senado ('JESUS FERNANDO REJAL') si es el único candidato
        alias = {}
        for kv in list(viejos):
            if kv in web_keys:
                continue
            cand = [kw for kw in web_keys if kw not in viejos and set(kv.split()) <= set(kw.split())]
            if len(cand) == 1:
                alias[cand[0]] = kv
        miembros, web_claves = [], set()
        for f in filas:
            if f["vacante"]:
                continue
            k = clave_nombre(f["nombre"])
            kv = alias.get(k, k)
            web_claves.add(kv)
            hit = por_clave.get(k)
            ref = hit[1] if hit else None
            nombre_ok = formato_nombre_padron(hit[0]) if hit else formato_nombre(f["nombre"])
            bloque = (ref or {}).get("bloque") or canon.get(clave_bloque(f["bloque"]), f["bloque"])
            cargo = CARGOS.get(f["cargo"], "")
            if kv in viejos:
                m = dict(viejos[kv])
                if m["nombre"] != nombre_ok and kv != k:
                    informe.append(f"NOMBRE en {c['nombre']}: '{m['nombre']}' -> '{nombre_ok}'")
                    m["nombre"] = nombre_ok
                if m.get("bloque") != bloque:
                    informe.append(f"BLOQUE en {c['nombre']}: {m['nombre']}: '{m.get('bloque')}' -> '{bloque}'")
                if m.get("rol", "") != cargo:
                    informe.append(f"CARGO en {c['nombre']}: {m['nombre']}: '{m.get('rol', '')}' -> '{cargo}'")
                m["bloque"], m["rol"] = bloque, cargo
            else:
                m = {"nombre": nombre_ok, "bloque": bloque, "rol": cargo}
                informe.append(f"ALTA en {c['nombre']}: {m['nombre']} ({bloque}) {cargo}".rstrip())
            miembros.append(m)
        for k, m in viejos.items():
            if k not in web_claves:
                informe.append(f"BAJA en {c['nombre']}: {m['nombre']}")
        cupo = len(filas)
        if c.get("cupo") != cupo:
            informe.append(f"CUPO en {c['nombre']}: {c.get('cupo')} -> {cupo}")
        n = dict(c)
        n["miembros"], n["cupo"] = miembros, cupo
        n["fuente"] = "senado"      # generar_web.py usa este roster y estos cargos
        nuevas.append(n)
        if not LOCAL:
            time.sleep(1.5)

    print(f"Comisiones leídas OK: {sum(1 for a, b in zip(coms, nuevas) if a is not b)} de {len(coms)}")
    if fallos:
        print(f"\nCOMISIONES NO LEÍDAS (quedan como estaban): {len(fallos)}")
        for x in fallos:
            print("  -", x)
    print(f"\nDIFERENCIAS CONTRA comisiones.json: {len(informe)}")
    for x in informe:
        print("  -", x)

    if not ACTUALIZAR:
        print("\n(modo comparación: no se escribió nada)")
        return
    if TEST:
        print("\n(TEST=1: no se escribió nada)")
        return
    if len(fallos) > 5:
        sys.exit("Demasiadas comisiones sin leer: no se actualiza nada (¿bloqueo o cambio de la página?).")
    if informe or any(c.get("fuente") != "senado" and n.get("fuente") == "senado" for c, n in zip(coms, nuevas)):
        json.dump(coms, open(BACKUP, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        json.dump(nuevas, open(COMISIONES_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"\ncomisiones.json actualizado (copia previa en {BACKUP})")
    else:
        print("\nSin cambios.")


if __name__ == "__main__":
    main()
