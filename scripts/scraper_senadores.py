#!/usr/bin/env python3
"""
scraper_senadores.py — Compara el padrón de senadores (data/senadores.json) con el
listado oficial del Senado "por bloque". MODO COMPARACIÓN: no modifica senadores.json.

Qué hace:
  1. Lee la página "Listado por bloque" del Senado (URL en SENADORES_BLOQUES_URL) o un
     HTML guardado (SENADORES_BLOQUES_HTML, para pruebas sin red).
  2. Extrae SOLO nombre de senador + bloque (no lee ni guarda el personal/asesores).
  3. Lo compara con los senadores vigentes de data/senadores.json y escribe un informe:
       - senadores que están en el Senado y no en el padrón (altas)
       - senadores del padrón (vigentes) que ya no figuran en el Senado (bajas)
       - senadores con bloque distinto
       - diferencias que son solo de escritura del nombre del bloque (informativas)
  4. Guarda data/senadores_diff.json (informe) y data/senadores_web.json (bloque por senador
     según el Senado). Con TEST=1 no escribe nada.

Variables de entorno:
    SENADORES_BLOQUES_URL   URL del listado por bloque (opcional: por defecto la oficial del Senado)
    SENADORES_BLOQUES_HTML  ruta a un HTML guardado (alternativa sin red)
    TEST                    "1" = solo imprime el informe, no escribe archivos

    ACTUALIZAR              "1" = además actualiza data/senadores.json (ver abajo)

Modo ACTUALIZAR=1 (escribe data/senadores.json):
  - vigente = figura en el listado oficial del Senado.
  - los que ya no figuran NO se borran: quedan con "vigente": false (conservan bloque
    y provincia, así los proyectos viejos no pierden su bloque).
  - el bloque se toma del Senado, respetando la grafía que ya usa el padrón cuando es
    el mismo bloque escrito distinto (p. ej. "Movere por Santa Cruz").
  - senadores nuevos: provincia "" (el listado por bloque no la trae); se completa
    en la próxima carga o con SENADORES_LISTA_URL (listado general), si se configura.
  - chequeos de seguridad: si el Senado devuelve menos de 60 senadores o menos de 8
    bloques, NO se escribe nada (puede ser una página rota o cambiada).
  - antes de escribir guarda data/senadores_backup.json.

Una sola consulta por corrida (dos si se configura SENADORES_LISTA_URL), User-Agent
propio e identificable.
"""
import json
import os
import re
import sys
import unicodedata

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
SENADORES_JSON = os.path.join(DATA_DIR, "senadores.json")
SALIDA_DIFF = os.path.join(DATA_DIR, "senadores_diff.json")
SALIDA_WEB = os.path.join(DATA_DIR, "senadores_web.json")

URL = (os.getenv("SENADORES_BLOQUES_URL", "").strip()
       or "https://www.senado.gob.ar/senadores/listados/agrupados-por-bloques")
HTML_LOCAL = os.getenv("SENADORES_BLOQUES_HTML", "").strip()
TEST = os.getenv("TEST", "") == "1"
ACTUALIZAR = os.getenv("ACTUALIZAR", "") == "1"
LISTA_URL = os.getenv("SENADORES_LISTA_URL", "").strip()
BACKUP = os.path.join(DATA_DIR, "senadores_backup.json")
COMISIONES_JSON = os.path.join(DATA_DIR, "comisiones.json")
UA = "HSN-Sistema-Legislativo/1.0 (herramienta interna de la Prosecretaria Parlamentaria; 1 consulta por corrida)"


def sin_tildes(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def normalizar_nombre(n):
    n = re.sub(r"^H\.S\.N\.\s*", "", (n or "").strip())
    n = " ".join(n.split())
    if "," in n:
        a, b = n.split(",", 1)
        n = f"{a.strip()}, {b.strip()}"
    return sin_tildes(n.upper())


def clave_bloque(b):
    """Para comparar bloques ignorando tildes, mayúsculas y la palabra 'por'."""
    b = sin_tildes((b or "").upper())
    b = re.sub(r"\bPOR\b", " ", b)
    return " ".join(b.split())


def obtener_html():
    if HTML_LOCAL:
        return open(HTML_LOCAL, encoding="utf-8", errors="replace").read()
    if not URL:
        sys.exit("Falta SENADORES_BLOQUES_URL (o SENADORES_BLOQUES_HTML para probar sin red).")
    import requests
    r = requests.get(URL, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    return r.text


def parsear(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    tabla = soup.find("table", class_="table-bordered")
    if tabla is None:
        sys.exit("No se encontró la tabla de bloques: el Senado pudo haber cambiado la página.")
    filas = (tabla.find("tbody") or tabla).find_all("tr", recursive=False)
    por_senador, por_bloque = {}, {}
    i = 0
    while i < len(filas):
        f = filas[i]
        celdas = f.find_all("td", recursive=False)
        if len(celdas) >= 3 and f.get("id") is None:
            bloque = " ".join(celdas[0].get_text(" ", strip=True).split())
            det = filas[i + 1] if i + 1 < len(filas) else None
            miembros, vistos = [], set()
            if det is not None and det.get("id"):
                for a in det.find_all("a", title=True):
                    t = a["title"]
                    if t.startswith("H.S.N.") and t not in vistos:   # solo senadores, no personal
                        vistos.add(t)
                        miembros.append(normalizar_nombre(t))
            por_bloque[bloque] = miembros
            for m in miembros:
                por_senador[m] = bloque
            i += 2
        else:
            i += 1
    if not por_senador:
        sys.exit("No se pudo extraer ningún senador: revisar el formato de la página.")
    return por_senador, por_bloque


def comparar(web):
    padron = json.load(open(SENADORES_JSON, encoding="utf-8"))
    vig = {normalizar_nombre(k): v for k, v in padron.items() if v.get("vigente")}
    altas = sorted(set(web) - set(vig))
    bajas = sorted(set(vig) - set(web))
    bloque_distinto, solo_grafia = [], []
    for k in sorted(set(web) & set(vig)):
        a, b = vig[k].get("bloque", ""), web[k]
        if sin_tildes(a.upper()) == sin_tildes(b.upper()):
            continue
        item = {"senador": k, "padron": a, "senado": b}
        (solo_grafia if clave_bloque(a) == clave_bloque(b) else bloque_distinto).append(item)
    return {"senadores_en_senado": len(web), "vigentes_en_padron": len(vig),
            "altas_en_senado_no_en_padron": altas, "bajas_en_padron_no_en_senado": bajas,
            "bloque_distinto": bloque_distinto, "solo_grafia_del_bloque": solo_grafia}


def provincias_desde_lista():
    """{NOMBRE_NORM: PROVINCIA} desde el listado general (opcional)."""
    if not LISTA_URL:
        return {}
    import requests
    from bs4 import BeautifulSoup
    r = requests.get(LISTA_URL, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    tabla = BeautifulSoup(r.text, "html.parser").find("table", id="senadoresTabla")
    out = {}
    if tabla is not None:
        for tr in tabla.find_all("tr")[1:]:
            td = tr.find_all("td")
            if len(td) >= 3:
                out[normalizar_nombre(td[1].get_text(" ", strip=True))] = \
                    " ".join(td[2].get_text(" ", strip=True).split()).upper()
    return out


def actualizar_padron(web, por_bloque):
    """Devuelve (padron_nuevo, cambios) sin escribir."""
    if len(web) < 60 or len(por_bloque) < 8:
        sys.exit(f"Chequeo de seguridad: solo {len(web)} senadores / {len(por_bloque)} bloques. "
                 "No se actualiza nada (la página pudo cambiar o estar incompleta).")
    padron = json.load(open(SENADORES_JSON, encoding="utf-8"))
    canon = {}
    for v in padron.values():
        canon.setdefault(clave_bloque(v.get("bloque", "")), v.get("bloque", ""))
    provs = provincias_desde_lista()
    nuevo, cambios = {}, []
    for k, v in padron.items():
        nuevo[k] = dict(v)
    por_norm = {normalizar_nombre(k): k for k in padron}
    for nombre, bloque_web in web.items():
        bloque = canon.get(clave_bloque(bloque_web), bloque_web)
        if nombre in por_norm:
            k = por_norm[nombre]
            ant = nuevo[k]
            if not ant.get("vigente"):
                cambios.append(f"REACTIVADO: {k}")
            if ant.get("bloque") != bloque:
                cambios.append(f"BLOQUE: {k}: '{ant.get('bloque')}' -> '{bloque}'")
            ant["bloque"], ant["vigente"] = bloque, True
        else:
            nuevo[nombre] = {"bloque": bloque, "provincia": provs.get(nombre, ""), "vigente": True}
            cambios.append(f"ALTA: {nombre} ({bloque})")
    for k, v in nuevo.items():
        if v.get("vigente") and normalizar_nombre(k) not in web:
            v["vigente"] = False
            cambios.append(f"BAJA (queda no vigente): {k}")
    return nuevo, cambios


def buscar_en_padron(por_norm, nombre):
    """Busca por nombre exacto; si no, por apellido + algún nombre de pila en común
    (p. ej. 'REJAL, Fernando' ~ 'REJAL, JESUS FERNANDO'), solo si hay un único candidato."""
    n = normalizar_nombre(nombre)
    if n in por_norm:
        return por_norm[n]
    ap, _, pila = n.partition(",")
    toks = set(pila.split())
    cand = [v for k, v in por_norm.items()
            if k.partition(",")[0].strip() == ap.strip() and toks & set(k.partition(",")[2].split())]
    return cand[0] if len(cand) == 1 else None


def sincronizar_comisiones(padron):
    """Alinea data/comisiones.json con el padrón: corrige el bloque de cada integrante
    y quita a los que ya no son senadores vigentes (el cupo queda como vacante).
    Devuelve (lista de cambios, comisiones_nuevas o None)."""
    if not os.path.exists(COMISIONES_JSON):
        return [], None
    coms = json.load(open(COMISIONES_JSON, encoding="utf-8"))
    por_norm = {normalizar_nombre(k): v for k, v in padron.items()}
    cambios = []
    for c in coms:
        nuevos = []
        for m in c.get("miembros", []):
            ref = buscar_en_padron(por_norm, m.get("nombre", ""))
            if ref is None:
                nuevos.append(m)          # no está en el padrón: no se toca
                continue
            if not ref.get("vigente"):
                cambios.append(f"QUITADO de {c['nombre']}: {m['nombre']} (ya no es senador vigente)")
                continue
            if m.get("bloque") != ref.get("bloque"):
                cambios.append(f"BLOQUE en {c['nombre']}: {m['nombre']}: '{m.get('bloque')}' -> '{ref.get('bloque')}'")
                m = dict(m, bloque=ref["bloque"])
            nuevos.append(m)
        c["miembros"] = nuevos
    return cambios, coms


def main():
    web, por_bloque = parsear(obtener_html())
    informe = comparar(web)
    print(f"Senado: {informe['senadores_en_senado']} senadores en {len(por_bloque)} bloques | "
          f"padrón: {informe['vigentes_en_padron']} vigentes")
    for titulo, clave in (("ALTAS (en el Senado, no en el padrón)", "altas_en_senado_no_en_padron"),
                          ("BAJAS (en el padrón como vigentes, no en el Senado)", "bajas_en_padron_no_en_senado")):
        print(f"\n{titulo}: {len(informe[clave])}")
        for x in informe[clave]:
            print("  -", x)
    print(f"\nBLOQUE DISTINTO: {len(informe['bloque_distinto'])}")
    for x in informe["bloque_distinto"]:
        print(f"  - {x['senador']}: padrón='{x['padron']}' | Senado='{x['senado']}'")
    print(f"\nSOLO DIFIERE LA ESCRITURA DEL BLOQUE: {len(informe['solo_grafia_del_bloque'])}")
    for x in informe["solo_grafia_del_bloque"]:
        print(f"  - {x['senador']}: padrón='{x['padron']}' | Senado='{x['senado']}'")
    if ACTUALIZAR:
        nuevo, cambios = actualizar_padron(web, por_bloque)
        print(f"\nACTUALIZAR: {len(cambios)} cambio(s) al padrón")
        for c in cambios:
            print("  -", c)
        if TEST:
            print("(TEST=1: no se escribió ningún archivo)")
            return
        cc, coms = sincronizar_comisiones(nuevo)
        print(f"COMISIONES: {len(cc)} cambio(s)")
        for c in cc:
            print("  -", c)
        if cc:
            json.dump(coms, open(COMISIONES_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        if cambios:
            os.makedirs(DATA_DIR, exist_ok=True)
            json.dump(json.load(open(SENADORES_JSON, encoding="utf-8")), open(BACKUP, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            json.dump(nuevo, open(SENADORES_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"senadores.json actualizado (copia previa en {BACKUP})")
        else:
            print("Sin cambios: senadores.json ya coincide con el Senado.")
        return
    if TEST:
        print("\n(TEST=1: no se escribió ningún archivo)")
        return
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(informe, open(SALIDA_DIFF, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump({"bloque_por_senador": web, "senadores_por_bloque": por_bloque},
              open(SALIDA_WEB, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nEscrito: {SALIDA_DIFF} y {SALIDA_WEB} (senadores.json NO se modificó)")


if __name__ == "__main__":
    main()
