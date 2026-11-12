"""Lee el PDF de una Orden del Día del Senado y extrae los datos de la Ayuda Memoria.

Prototipo. Del PDF salen: número, tipo (normal/anexo), fecha de la OD, comisión cabecera,
texto «autores y contenido» (el sumario), fecha del dictamen y firmantes.
"""
import re

import pdfplumber

MESES = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
     "septiembre", "octubre", "noviembre", "diciembre"], 1)}
RE_FECHA = r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})"
RE_FIN_FIRMANTES = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{2,}\.$")  # termina en apellido + punto (no en inicial)


RE_DISIDENCIA = re.compile(r"^en\s+disidencia\s*(parcial|total)?\s*:\s*", re.I)


def _lista_nombres(lineas, desde, maximo=16):
    """Junta renglones hasta que la lista cierra con «Apellido.» y la parte en nombres.
    Devuelve (nombres, índice del renglón siguiente, si cerró bien)."""
    acumulado, cerrado, k = "", False, desde
    while k < len(lineas) and k < desde + maximo:
        acumulado = (acumulado + " " + lineas[k]).strip()
        k += 1
        if RE_FIN_FIRMANTES.search(acumulado):
            cerrado = True
            break
    partes = re.split(r"\s+[–—-]\s+", re.sub(r"\s+", " ", acumulado))
    return [p.strip().rstrip(".").strip() for p in partes if p.strip()], k, cerrado


def _fecha(m):
    return f"{int(m.group(1)):02d}/{MESES[m.group(2).lower()]:02d}/{m.group(3)}"


RE_ENCABEZADO = re.compile(r"^[“\"]?\s*20\d\d\s*-\s*A[ñn]o\b", re.I)  # «2026 - Año del 120 Aniversario…»


def texto_pdf(ruta, paginas=None, hasta_firmantes=False):
    """Texto del PDF, sin el encabezado que se repite arriba de cada página
    (si no, se mete en el medio de las listas que cortan de página).
    hasta_firmantes=True deja de leer cuando ya pasaron los firmantes (los PDF pueden tener 70+ páginas)."""
    textos, lineas_desde_sala = [], None
    with pdfplumber.open(ruta) as pdf:
        pags = pdf.pages if paginas is None else pdf.pages[:paginas]
        for p in pags:
            ls = [l for l in (p.extract_text() or "").splitlines() if not RE_ENCABEZADO.match(l.strip())]
            textos.append("\n".join(ls))
            if hasta_firmantes:
                for l in ls:
                    if lineas_desde_sala is not None:
                        lineas_desde_sala += 1
                    elif re.match(r"\s*sala de la", l, re.I):
                        lineas_desde_sala = 0
                if lineas_desde_sala is not None and lineas_desde_sala >= 20:
                    break
    return "\n".join(textos)


def leer_od(ruta):
    t = texto_pdf(ruta, hasta_firmantes=True)
    lineas = [l.strip() for l in t.splitlines()]
    out = {"periodo": None, "numero": None, "tipo": "NORMAL", "fecha_od": None, "comision": None,
           "comisiones_texto": None, "sumario": None, "fecha_dictamen": None, "firmantes": [], "disidencias": [], "firmantes_todos": [], "minoria": False, "avisos": []}

    m = re.search(r"(ANEXO AL )?ORDEN DEL D[IÍ]A\s*N[º°o]\s*(\d+)", t, re.I)
    if m:
        out["numero"] = int(m.group(2))
        out["tipo"] = "ANEXO" if m.group(1) else "NORMAL"
    else:
        out["avisos"].append("no se encontró el número de OD")

    mp = re.search(r"SESIONES\s+ORDINARIAS\s+DE\s+(\d{4})", t, re.I)
    if mp:
        out["periodo"] = int(mp.group(1))

    # Fecha de la OD: primera fecha que aparece después del título
    if m:
        f = re.search(RE_FECHA, t[m.end():m.end() + 200], re.I)
        if f:
            out["fecha_od"] = _fecha(f)

    # Sumario: entre «SUMARIO» y «DICTAMEN DE COMISIÓN»
    try:
        i = next(k for k, l in enumerate(lineas) if l.upper() == "SUMARIO")
        j = next(k for k in range(i + 1, len(lineas)) if lineas[k].upper().startswith("DICTAMEN DE COMISI"))
        bloque = [l for l in lineas[i + 1:j] if l]
        # Puede haber varias comisiones, en varios renglones («COMISIÓN DE X, DE Y Y DE Z»):
        # llegan hasta el renglón que empieza con «Dictamen» (ahí arranca el texto del sumario).
        corte = next((k for k, l in enumerate(bloque) if re.match(r"dictamen\b", l, re.I)), None)
        if corte is None and bloque and bloque[0].upper().startswith("COMISI"):
            corte = 1
        corte = corte or 0
        comisiones = re.sub(r"\s+", " ", " ".join(bloque[:corte])).strip()
        out["comisiones_texto"] = comisiones
        # Cabecera = la primera comisión nombrada
        primera = re.sub(r"^COMISI[ÓO]N(?:ES)?\s+DE\s+", "", comisiones, flags=re.I)
        # Se separa solo en «, DE» / «Y DE»: hay comisiones con coma en el nombre
        # (p. ej. «SISTEMAS, MEDIOS DE COMUNICACIÓN Y LIBERTAD DE EXPRESIÓN»).
        out["comision"] = re.split(r",\s+DE\s+|\s+Y\s+DE\s+", primera, maxsplit=1, flags=re.I)[0].strip() or None
        out["sumario"] = re.sub(r"\s+", " ", " ".join(bloque[corte:])).strip()
        out["minoria"] = "MINOR" in " ".join(lineas[j:j + 3]).upper()
    except StopIteration:
        out["avisos"].append("no se encontró el sumario")

    # Fecha del dictamen y firmantes: «Sala de la comisión, <fecha>.» y las líneas que siguen
    try:
        k = next(k for k, l in enumerate(lineas) if re.match(r"sala de la", l, re.I))
        f = re.search(RE_FECHA, lineas[k], re.I)
        if f:
            out["fecha_dictamen"] = _fecha(f)
        out["firmantes"], k, cerrado = _lista_nombres(lineas, k + 1)
        if not cerrado or not out["firmantes"]:
            out["avisos"].append("la lista de firmantes no se cerró bien: revisar")
        # Después pueden venir «En disidencia parcial: A – B.» / «En disidencia total: …»
        while k < len(lineas) and RE_DISIDENCIA.match(lineas[k]):
            m = RE_DISIDENCIA.match(lineas[k])
            lineas[k] = lineas[k][m.end():].strip()
            nombres, k, cerrado = _lista_nombres(lineas, k)
            out["disidencias"].append({"tipo": (m.group(1) or "").lower() or "sin aclarar", "firmantes": nombres})
            if not cerrado:
                out["avisos"].append("una lista de disidencia no se cerró bien: revisar")
    except StopIteration:
        out["avisos"].append("no se encontró «Sala de la comisión»")
    # Como los carga hoy la Ayuda Memoria: firmantes + quienes firmaron en disidencia, todos juntos
    out["firmantes_todos"] = out["firmantes"] + [n for d in out["disidencias"] for n in d["firmantes"]]
    return out
