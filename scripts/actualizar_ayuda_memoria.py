"""Arma la Ayuda Memoria completa y sola, sin planilla de Excel.

Regla (comprobada contra la planilla manual): la Ayuda Memoria = las Órdenes del Día cuyo ESTADO en el
sitio del Senado es PENDIENTE. Para cada una, los datos salen del PDF de la OD.

Qué hace, en orden:
  1. Toma las OD del año de data/od.json (la lista que ya mantiene el scraper de Mariano).
  2. Consulta en el Senado el ESTADO de cada una (ficha del expediente, tabla «Órdenes del Día»).
     Lo que ya está resuelto (aprobada, rechazada…) se recuerda y no se vuelve a consultar;
     las PENDIENTES y las nuevas sí se consultan en cada corrida.
  3. Baja los PDF de las pendientes (y de sus anexos) que todavía no estén.
  4. Lee los PDF y escribe data/ayuda_memoria_auto.json (mismo formato que data/ayuda_memoria.json).

NO modifica data/ayuda_memoria.json: la copia es decisión de quien lo use.

Uso (desde la raíz del repo):

  # la primera vez consulta todas las OD del año (unas 400 fichas, ~7 minutos); después, solo las pendientes y las nuevas
  py scripts/actualizar_ayuda_memoria.py --pdfs pdfs_od

  # compararla con la planilla manual (qué entra, qué sale y qué cambia en las que están en las dos)
  py scripts/actualizar_ayuda_memoria.py --pdfs pdfs_od --comparar data/ayuda_memoria_manual.json

  # solo ver cuántas fichas y PDF faltan, sin consultar nada
  py scripts/actualizar_ayuda_memoria.py --pdfs pdfs_od --solo-contar

Es amable con el sitio: User-Agent propio, 1 segundo de pausa entre pedidos, y se detiene si fallan 3 seguidos.
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generar_ayuda_memoria as gam  # noqa: E402
import verificar_estado_od as veo  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdfs", required=True, help="carpeta donde se guardan los PDF de las OD")
    ap.add_argument("--salida", default=os.path.join(gam.DATA, "ayuda_memoria_auto.json"))
    ap.add_argument("--estados", default=os.path.join(gam.DATA, "estado_od.json"),
                    help="archivo donde se recuerdan los estados ya consultados")
    ap.add_argument("--comparar", help="JSON a comparar (por ejemplo data/ayuda_memoria_manual.json)")
    ap.add_argument("--anio", type=int, default=2026)
    ap.add_argument("--solo-contar", action="store_true", help="no consulta ni baja nada: solo dice cuánto haría falta")
    a = ap.parse_args()

    od_todas = gam.cargar("od.json", [])
    normales = {o["nro_od"]: o for o in od_todas if o["anio_od"] == a.anio and o["tipo_od"] == "N"}
    estados = {}
    if os.path.exists(a.estados):
        with open(a.estados, encoding="utf-8") as f:
            estados = json.load(f)

    # --- 1 y 2: estado de cada OD
    def resuelta(n):
        e = (estados.get(str(n)) or {}).get("estado")
        return bool(e) and e != "PENDIENTE"  # lo ya resuelto no se vuelve a mirar

    por_consultar = sorted(n for n in normales if not resuelta(n))
    print(f"{len(normales)} OD de {a.anio} en data/od.json; {len(normales) - len(por_consultar)} ya resueltas; "
          f"se consultan {len(por_consultar)} fichas")

    if a.solo_contar:
        pendientes_conocidas = sorted(n for n in normales if (estados.get(str(n)) or {}).get("estado") == "PENDIENTE")
        faltan_pdf = [n for n in pendientes_conocidas if not os.path.exists(os.path.join(a.pdfs, f"{a.anio}_{n:04d}_N.pdf"))]
        print(f"Hoy se conocen {len(pendientes_conocidas)} pendientes; a {len(faltan_pdf)} les falta el PDF")
        return

    import requests
    sesion = requests.Session()
    seguidas_malas = 0
    for i, n in enumerate(por_consultar, 1):
        estado, fecha, probadas, seguidas_malas = veo.estado_de_od(normales[n], a.anio, sesion, seguidas_malas)
        if seguidas_malas >= 3:
            print("Se detiene: 3 pedidos seguidos fallaron. Probá más tarde (lo ya consultado quedó guardado).")
            break
        previo = estados.get(str(n)) or {}
        if not estado and previo.get("estado"):
            # Si el pedido falló (corte de red del sitio), se conserva lo que ya se sabía de esa OD:
            # así una OD pendiente no desaparece de la Ayuda Memoria por un error pasajero.
            estado, fecha = previo["estado"], previo.get("fecha")
        estados[str(n)] = {"estado": estado, "fecha": fecha, "expedientes_probados": probadas}
        if i % 10 == 0 or i == len(por_consultar):
            print(f"  [{i}/{len(por_consultar)}] consultadas…")
        with open(a.estados, "w", encoding="utf-8") as f:
            json.dump(estados, f, ensure_ascii=False, indent=2)

    pendientes = sorted(n for n in normales if (estados.get(str(n)) or {}).get("estado") == "PENDIENTE")
    sin_leer = sorted(n for n in normales if str(n) in estados and not estados[str(n)].get("estado"))
    resumen = {}
    for n in normales:
        e = (estados.get(str(n)) or {}).get("estado")
        resumen[e] = resumen.get(e, 0) + 1
    print("Estados:", dict(sorted(resumen.items(), key=lambda kv: -kv[1])))
    if sin_leer:
        print("AVISO: no se pudo leer el estado de", sin_leer)

    # --- 3: PDF de las pendientes (normal y anexo)
    gam.descargar(set(pendientes), a.pdfs, a.anio)

    # --- 4: leer solo los PDF de las pendientes
    rutas = []
    for n in pendientes:
        for tipo in ("N", "A"):
            ruta = os.path.join(a.pdfs, f"{a.anio}_{n:04d}_{tipo}.pdf")
            if os.path.exists(ruta):
                rutas.append(ruta)
    od_idx = {(o["nro_od"], o["anio_od"], o["tipo_od"]): o for o in od_todas}
    proy_idx = {(p["origen"], p["nro"], p["anio"]): p for p in gam.cargar("proyectos.json", [])}
    filas, problemas = gam.leer_pdfs(rutas, od_idx, proy_idx)
    filas.sort(key=lambda f: (f["periodo"], int(f["numero"])), reverse=True)
    with open(a.salida, "w", encoding="utf-8") as f:
        json.dump(filas, f, ensure_ascii=False, indent=2)
    print(f"{len(pendientes)} OD pendientes -> {len(filas)} fichas (con anexos) en {a.salida}")
    for donde, que in problemas:
        print(f"AVISO {donde}: {que}")

    if a.comparar:
        with open(a.comparar, encoding="utf-8") as f:
            ref = json.load(f)
        en_ref = {int(x["numero"]) for x in ref if x.get("periodo") == a.anio}
        entran = sorted(set(pendientes) - en_ref)
        salen = sorted(en_ref - set(pendientes))
        print(f"\n=== Comparación de QUÉ OD entran, con {a.comparar}")
        print(f"Pendientes en el Senado: {len(pendientes)} | en la planilla: {len(en_ref)}")
        print("Entrarían (pendientes que la planilla no tiene):", entran or "ninguna")
        print("Saldrían (la planilla las tiene pero ya no están pendientes):", salen or "ninguna")
        gam.comparar(filas, a.comparar)


if __name__ == "__main__":
    main()
