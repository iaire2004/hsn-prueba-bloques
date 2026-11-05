#!/usr/bin/env python3
"""
autoria_caratula.py — Autoría de un proyecto según el prefijo de la carátula
============================================================================
Módulo compartido por scripts/aplicar_trazabilidad_csv.py y scripts/scraper_proyectos.py.

La carátula de un expediente del Senado empieza con los autores reales:
    "FAMA: PROYECTO DE LEY ..."                       -> Fama
    "CAPITANICH Y BAHL: PROYECTO DE LEY ..."          -> Capitanich y Bahl (cada uno cuenta)
    "SORIA Y OTROS: PROYECTO DE LEY ..."              -> sólo Soria (los demás firmantes se ignoran)
    "VARIOS SENADORES: ..."                           -> sin cambios (no se calcula nada)

La columna AUTOR de la trazabilidad (y el campo `autores` de proyectos.json) trae
a TODOS los firmantes en un orden que no refleja la autoría; por eso se calcula
aparte, en dos campos nuevos que no reemplazan a los existentes:

    autores_caratula  lista de senadores nombrados en el prefijo (mismo formato que `autores`)
    bloques_caratula  lista alineada: bloque de cada uno (no deduplicada)

Bloque de cada autor: el bloque ACTUAL según data/senadores.json (el proyecto sigue a
su senador: si cambia de bloque, sus proyectos pasan al nuevo). Si el senador no figura,
"Sin datos". Las páginas por bloque no dependen de este valor guardado: recalculan el
bloque de cada autor al generarse; `bloques_caratula` se mantiene por compatibilidad.

Sin dependencias externas (no importa el scraper) para poder usarse desde ambos lados.
"""
import difflib
import re
import unicodedata

SIN_DATOS = "Sin datos"


def sin_tildes(texto):
    return "".join(
        c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn"
    )


def _clave(texto):
    """Mayúsculas, sin tildes y con espacios colapsados."""
    return re.sub(r"\s+", " ", sin_tildes(texto).upper()).strip()


def _apellido(autor):
    return _clave((autor or "").split(",")[0])


def parsear_prefijo(caratula):
    """Devuelve {'apellidos': [...], 'varios': bool, 'y_otros': bool} o None si la
    carátula no tiene prefijo ('X: ...')."""
    if not caratula or ":" not in caratula:
        return None
    prefijo = _clave(caratula.split(":", 1)[0])
    if not prefijo:
        return None
    if re.search(r"\bVARIOS\s+(SENORES\s+)?SENADOR", prefijo):
        return {"apellidos": [], "varios": True, "y_otros": False}
    y_otros = bool(re.search(r"\bY\s+OTR[OA]S?\b", prefijo))
    limpio = re.sub(r"\s*\bY\s+OTR[OA]S?\b", "", prefijo).strip()
    partes = re.split(r"\s*,\s*|\s+Y\s+", limpio)
    return {"apellidos": [p.strip() for p in partes if p.strip()], "varios": False, "y_otros": y_otros}


def _buscar_en_padron(apellido, padron):
    """Senadores del padrón (vigentes o no) cuyo apellido coincide exacto; lista de nombres."""
    return [n for n in padron if _apellido(n) == apellido]


def _nombre_pila(autor):
    return _clave((autor or "").partition(",")[2]).replace(".", "")


def _coincide_nombre(resto, autor):
    """'C' / 'FLORENCIA' / 'MARIA FLORENCIA' contra el nombre de pila del autor."""
    resto = resto.replace(".", "").strip()
    nombre = _nombre_pila(autor)
    if not resto or not nombre:
        return False
    if len(resto) == 1:
        return nombre.startswith(resto)
    return any(w == resto for w in nombre.split()) or nombre.startswith(resto)


def vincular_apellido(token, candidatos, padron):
    """Vincula un token del prefijo con un senador.
    candidatos: autores del expediente ('APELLIDO, NOMBRE'), en orden.
    Prioridad: apellido exacto entre los autores del expediente; 'APELLIDO + nombre o
    inicial' ('LOPEZ C.', 'LOPEZ FLORENCIA') para desempatar a quienes comparten apellido;
    inclusión; apellido único en el padrón; error de tipeo (similitud >= 0,8).
    Si hay varios autores con el mismo apellido y el token no los distingue, se toma el
    primero de la lista (el principal) y se marca ambiguo.
    Devuelve (nombre | None, ambiguo: bool)."""
    token = _clave(token).replace(".", " ").strip()
    token = re.sub(r"\s+", " ", token)
    exactos = [c for c in candidatos if _apellido(c) == token]
    if exactos:
        return exactos[0], len(exactos) > 1
    # 'APELLIDO nombre/inicial'
    for c in candidatos:
        ap = _apellido(c)
        if token.startswith(ap + " ") and _coincide_nombre(token[len(ap):], c):
            return c, False
    incluidos = [c for c in candidatos
                 if len(token) >= 4 and (token in _apellido(c) or _apellido(c) in token)]
    if len(incluidos) == 1:
        return incluidos[0], False
    en_padron = _buscar_en_padron(token, padron)
    if len(en_padron) == 1:
        return en_padron[0], False
    if not en_padron:
        aps = {}
        for c in candidatos:
            aps.setdefault(_apellido(c), c)
        parecidos = difflib.get_close_matches(token, list(aps), n=1, cutoff=0.8)
        if parecidos:
            return aps[parecidos[0]], False
    return None, len(en_padron) > 1


def _unir_nombres_de_pila(tokens, candidatos):
    """'LOPEZ, FLORENCIA' se parte en ['LOPEZ', 'FLORENCIA']: si el segundo es el nombre de
    pila de un autor de apellido igual al primero, se vuelve a unir."""
    out = []
    for t in tokens:
        t2 = _clave(t).replace(".", "")
        if out and any(_apellido(c) == _clave(out[-1]) and _coincide_nombre(t2, c) for c in candidatos)                 and not any(_apellido(c) == t2 for c in candidatos):
            out[-1] = out[-1] + " " + t
        else:
            out.append(t)
    return out


def bloque_actual(autor, padron):
    """Bloque del senador según el padrón (nombre exacto; si no, apellido único)."""
    if autor in padron:
        return padron[autor].get("bloque") or SIN_DATOS
    clave = _clave(autor)
    for nombre, info in padron.items():
        if _clave(nombre) == clave:
            return info.get("bloque") or SIN_DATOS
    ap = _apellido(autor)
    cands = _buscar_en_padron(ap, padron)
    if len(cands) == 1:
        return padron[cands[0]].get("bloque") or SIN_DATOS
    return SIN_DATOS


def es_vigente(autor, padron):
    """¿El senador figura como vigente en el padrón? (nombre exacto o sin tildes)"""
    if autor in padron:
        return bool(padron[autor].get("vigente"))
    clave = _clave(autor)
    return any(_clave(n) == clave and info.get("vigente") for n, info in padron.items())


def calcular_autoria(caratula, autores_firmantes, padron):
    """Calcula (autores_caratula, bloques_caratula, info) para un expediente.

    caratula            texto completo de la carátula (con prefijo)
    autores_firmantes   todos los firmantes ('APELLIDO, NOMBRE'), ya normalizados
    padron              data/senadores.json (dict nombre -> {bloque, provincia, vigente})

    Si el prefijo no nombra a ningún senador (o es 'VARIOS SENADORES'), devuelve
    ([], [], info) y el llamador no debe guardar los campos nuevos.
    info: {'varios', 'sin_vincular': [...], 'ambiguos': [...]} (para el informe)."""
    info = {"varios": False, "sin_vincular": [], "ambiguos": []}
    pref = parsear_prefijo(caratula)
    if pref is None:
        return [], [], info
    if pref["varios"]:
        info["varios"] = True
        return [], [], info
    autores, bloques = [], []
    vistos = set()
    tokens = _unir_nombres_de_pila(pref["apellidos"], autores_firmantes)
    for ap in tokens:
        nombre, ambiguo = vincular_apellido(ap, autores_firmantes, padron)
        if ambiguo:
            info["ambiguos"].append(ap)
        if nombre is None:
            info["sin_vincular"].append(ap)
            continue
        if _clave(nombre) in vistos:
            continue
        vistos.add(_clave(nombre))
        autores.append(nombre)
        bloques.append(bloque_actual(nombre, padron))
    if len(autores) != len(tokens):
        # El prefijo nombra a alguien que no es senador/a identificable: la carátula
        # no es del tipo 'AUTOR: ...'; se descarta lo calculado sólo si no hay ninguno.
        if not autores:
            return [], [], info
    return autores, bloques, info
