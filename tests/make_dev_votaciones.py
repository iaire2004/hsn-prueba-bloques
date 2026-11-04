"""Genera data/votaciones.json de DESARROLLO con 30 de las 46 votaciones en general de 2026,
leídas a mano del sitio del Senado el 15-10-2026 (el sitio frenó el acceso antes de poder leer el resto).
Sólo trae el resumen por bloque (sin voto nominal). Lo reemplaza el scraper al correr en el repo de la organización."""
import json, sys, os
B = ["CONVICCIÓN FEDERAL","DESPIERTA CHUBUT","FRENTE CÍVICO POR SANTIAGO","FRENTE PRO","INDEPENDENCIA",
     "JUSTICIA SOCIAL FEDERAL","JUSTICIALISTA","LA LIBERTAD AVANZA","LA NEUQUINIDAD","MOVERE SANTA CRUZ",
     "MOVIMIENTO POR MISIONES","PRIMERO LOS SALTEÑOS","PROVINCIAS UNIDAS","UCR - UNIÓN CÍVICA RADICAL"]
# (id, fecha, nro, tipo, titulo, ods (lista corta), cantidad_ods, conteos por bloque a,n,b,x)
A = [
(2829,"24-09-2026",2,"EN GENERAL","Modificación de la Carta Orgánica del Banco Central.",["367/2026"],1,
 "3,0,0,0 1,0,0,0 0,1,0,1 3,0,0,0 1,0,0,0 0,2,0,0 0,19,0,2 21,0,0,0 1,0,0,0 2,0,0,0 2,0,0,0 1,0,0,0 1,0,0,1 10,0,0,0"),
(2846,"24-09-2026",21,"EN GENERAL Y EN PARTICULAR","Modificación del Régimen de Zonas Frías.",["402/2026"],1,
 "3,0,0,0 1,0,0,0 0,0,0,2 3,0,0,0 1,0,0,0 0,0,0,2 0,0,0,21 21,0,0,0 1,0,0,0 0,2,0,0 2,0,0,0 1,0,0,0 1,0,0,1 4,6,0,0"),
(2806,"17-09-2026",2,"EN GENERAL Y EN PARTICULAR","Acuerdo para designaciones en el Poder Judicial.",["338/2026","353/2026","354/2026"],3,
 "3,0,0,0 1,0,0,0 2,0,0,0 3,0,0,0 1,0,0,0 2,0,0,0 19,0,0,2 20,0,0,1 1,0,0,0 2,0,0,0 2,0,0,0 1,0,0,0 2,0,0,0 7,0,0,3"),
(2807,"17-09-2026",3,"EN GENERAL Y EN PARTICULAR","Traspaso de la Justicia Nacional a la Ciudad Autónoma de Buenos Aires.",["360/2026","361/2026"],2,
 "3,0,0,0 1,0,0,0 0,2,0,0 3,0,0,0 1,0,0,0 0,2,0,0 0,17,0,4 20,0,0,1 1,0,0,0 2,0,0,0 2,0,0,0 1,0,0,0 1,0,0,1 9,0,0,1"),
(2808,"17-09-2026",4,"EN GENERAL","Inocencia Fiscal II.",["372/2026"],1,
 "3,0,0,0 1,0,0,0 0,2,0,0 3,0,0,0 1,0,0,0 0,2,0,0 0,19,0,2 20,0,0,1 1,0,0,0 2,0,0,0 2,0,0,0 1,0,0,0 1,0,0,1 9,0,0,1"),
(2813,"17-09-2026",9,"EN GENERAL Y EN PARTICULAR","Designación de cónsules y vicecónsules honorarios.",["340/2026","341/2026","342/2026"],12,
 "3,0,0,0 1,0,0,0 2,0,0,0 3,0,0,0 1,0,0,0 2,0,0,0 17,0,0,4 20,0,0,1 1,0,0,0 2,0,0,0 2,0,0,0 1,0,0,0 1,0,0,1 8,0,0,2"),
(2814,"17-09-2026",10,"EN GENERAL Y EN PARTICULAR","Reconocimiento a Héroes Nacionales.",["337/2026"],1,
 "3,0,0,0 0,0,0,1 2,0,0,0 3,0,0,0 1,0,0,0 1,0,0,1 18,0,0,3 16,0,0,5 1,0,0,0 2,0,0,0 2,0,0,0 0,1,0,0 1,0,0,1 7,0,0,3"),
(2815,"17-09-2026",11,"EN GENERAL Y EN PARTICULAR","Declaración de Héroe Nacional al Brigadier Estanislao López.",["363/2026"],1,
 "3,0,0,0 0,0,0,1 2,0,0,0 3,0,0,0 1,0,0,0 2,0,0,0 18,0,0,3 16,0,0,5 1,0,0,0 2,0,0,0 2,0,0,0 0,1,0,0 1,0,0,1 7,0,0,3"),
(2816,"17-09-2026",12,"EN GENERAL Y EN PARTICULAR","Institución de Día Nacional en Honor al Almirante Guillermo Brown.",["365/2026"],1,
 "3,0,0,0 0,0,0,1 2,0,0,0 3,0,0,0 1,0,0,0 2,0,0,0 18,0,0,3 17,0,0,4 1,0,0,0 2,0,0,0 2,0,0,0 1,0,0,0 1,0,0,1 7,0,0,3"),
(2817,"17-09-2026",13,"EN GENERAL Y EN PARTICULAR","Creación del Parque Interjurisdiccional Marino Monte León",["339/2026"],1,
 "3,0,0,0 0,0,0,1 2,0,0,0 3,0,0,0 1,0,0,0 2,0,0,0 18,0,0,3 16,0,0,5 1,0,0,0 2,0,0,0 2,0,0,0 1,0,0,0 1,0,0,1 7,0,0,3"),
(2819,"17-09-2026",15,"EN GENERAL","Marco Regulatorio de Biocombustibles.",["362/2026"],1,
 "3,0,0,0 1,0,0,0 0,2,0,0 3,0,0,0 1,0,0,0 0,2,0,0 1,18,0,2 19,0,0,2 1,0,0,0 0,2,0,0 2,0,0,0 1,0,0,0 2,0,0,0 7,1,0,2"),
(2801,"27-08-2026",1,"EN GENERAL Y EN PARTICULAR","Acuerdo para designaciones en el Poder Judicial y el Ministerio Público Fiscal.",["243/2026","244/2026","245/2026"],62,
 "3,0,0,0 1,0,0,0 2,0,0,0 2,0,0,1 1,0,0,0 2,0,0,0 18,0,0,3 20,0,0,1 1,0,0,0 2,0,0,0 2,0,0,0 1,0,0,0 2,0,0,0 9,0,0,1"),
(2802,"27-08-2026",2,"EN GENERAL Y EN PARTICULAR","Acuerdo para designar Vocal de la Cámara Nacional de Apelaciones en lo Criminal y Correccional Federal de la Capital Federal, Sala I, a Pablo Daniel Bertuzzi.",["292/2026"],1,
 "3,0,0,0 1,0,0,0 0,2,0,0 2,0,0,1 1,0,0,0 0,2,0,0 0,19,0,2 20,0,0,1 1,0,0,0 2,0,0,0 2,0,0,0 1,0,0,0 2,0,0,0 9,0,0,1"),
(2803,"27-08-2026",3,"EN GENERAL Y EN PARTICULAR","Tratado con Ucrania sobre Traslado de Personas Sentenciadas. Enmienda al Protocolo de Montevideo sobre el Comercio de Servicios del Mercosur. Tratado de Extradición con la República de Chile. Tratado de Medellín. Acuerdo de Libre Comercio entre los Estados de la Asociación Europea de Libre Comercio (AELC) y el Mercosur.",["114/2026","115/2026","120/2026","121/2026","257/2026"],5,
 "3,0,0,0 1,0,0,0 2,0,0,0 2,0,0,1 1,0,0,0 2,0,0,0 19,0,0,2 18,0,0,3 1,0,0,0 2,0,0,0 2,0,0,0 1,0,0,0 2,0,0,0 9,0,0,1"),
(2804,"27-08-2026",4,"EN GENERAL Y EN PARTICULAR","Declaración como Fiesta Nacional al Festival del Membrillo, Departamento Ambato, provincia de Catamarca. Declaración de Fiesta Nacional del Mate y la Amistad, a realizarse en Virasoro, provincia de Corrientes. Declaración a Bernabé Araóz como Héroe Nacional.",["136/2026","139/2026","275/2026"],3,
 "3,0,0,0 1,0,0,0 2,0,0,0 2,0,0,1 1,0,0,0 2,0,0,0 19,0,0,2 18,0,0,3 1,0,0,0 2,0,0,0 2,0,0,0 1,0,0,0 2,0,0,0 9,0,0,1"),
(2796,"06-08-2026",8,"EN GENERAL","Inviolabilidad de la Propiedad Privada.",["104/2026"],1,
 "0,3,0,0 1,0,0,0 0,2,0,0 3,0,0,0 0,1,0,0 0,2,0,0 0,20,0,1 21,0,0,0 0,1,0,0 0,2,0,0 2,0,0,0 0,1,0,0 1,1,0,0 9,0,0,1"),
(2789,"16-07-2026",1,"EN GENERAL Y EN PARTICULAR","Acuerdos para el ascenso de diplomáticos pertenecientes al Ministerio de Relaciones Exteriores, Comercio Internacional y Culto.",["22/2026","23/2026","24/2026"],6,
 "3,0,0,0 0,0,0,1 2,0,0,0 2,0,0,1 1,0,0,0 2,0,0,0 20,0,0,1 21,0,0,0 1,0,0,0 2,0,0,0 2,0,0,0 1,0,0,0 1,0,0,1 9,0,0,1"),
(2790,"16-07-2026",2,"EN GENERAL Y EN PARTICULAR","Acuerdo para designaciones en el Poder Judicial, Ministerio Público Fiscal y Ministerio Público de la Defensa de la Nación.",["123/2026","125/2026","126/2026"],27,
 "3,0,0,0 0,0,0,1 2,0,0,0 2,0,0,1 1,0,0,0 2,0,0,0 20,0,0,1 21,0,0,0 1,0,0,0 0,2,0,0 2,0,0,0 1,0,0,0 1,0,0,1 9,0,0,1"),
(2791,"16-07-2026",3,"EN GENERAL Y EN PARTICULAR","Acuerdo para posibilitar un nuevo nombramiento del Vocal de la Cámara Nacional de Apelaciones del Trabajo de la Capital Federal, Sala VIII, al Dr. Víctor Arturo Pesino.",["124/2026"],1,
 "0,3,0,0 0,0,0,1 0,2,0,0 2,0,0,1 1,0,0,0 0,2,0,0 0,20,0,1 21,0,0,0 1,0,0,0 0,2,0,0 2,0,0,0 1,0,0,0 0,1,0,1 7,2,0,1"),
(2792,"16-07-2026",4,"EN GENERAL Y EN PARTICULAR","Acuerdo para designar Vocal de la Cámara Nacional de Apelaciones en lo Comercial de la Capital Federal, Sala C, al Dr. Javier Jorge Cosentino.",["216/2026"],1,
 "3,0,0,0 0,0,0,1 0,2,0,0 2,0,0,1 1,0,0,0 0,2,0,0 1,19,0,1 21,0,0,0 0,1,0,0 0,2,0,0 2,0,0,0 0,0,0,1 1,0,0,1 9,0,0,1"),
(2793,"16-07-2026",5,"EN GENERAL Y EN PARTICULAR","Declaración de la ciudad de San Miguel de Tucumán como capital simbólica de la República Argentina, el 9 de julio de cada año.",["152/2026"],1,
 "3,0,0,0 0,0,0,1 2,0,0,0 2,0,0,1 1,0,0,0 2,0,0,0 20,0,0,1 21,0,0,0 1,0,0,0 2,0,0,0 2,0,0,0 1,0,0,0 0,0,0,2 10,0,0,0"),
(2764,"04-06-2026",2,"EN GENERAL Y EN PARTICULAR","Acuerdo para designaciones en el Poder Judicial, Ministerio Público Fiscal y Ministerio Público de la Defensa de la Nación.",["29/2026","30/2026","31/2026"],13,
 "3,0,0,0 1,0,0,0 2,0,0,0 2,0,0,1 1,0,0,0 2,0,0,0 17,0,0,4 20,0,0,1 0,0,0,1 2,0,0,0 2,0,0,0 1,0,0,0 1,0,0,1 10,0,0,0"),
(2765,"04-06-2026",3,"EN GENERAL Y EN PARTICULAR","Acuerdo para designar a la Jueza de Cámara del Tribunal Oral en lo Criminal Federal N°3 de La Plata María Julia Sosa.",["42/2026"],1,
 "3,0,0,0 1,0,0,0 0,2,0,0 2,0,0,1 1,0,0,0 0,2,0,0 1,16,0,4 20,0,0,1 0,0,0,1 0,2,0,0 2,0,0,0 1,0,0,0 1,0,0,1 10,0,0,0"),
(2766,"04-06-2026",4,"EN GENERAL Y EN PARTICULAR","Acuerdo para designaciones en el Poder Judicial, Ministerio Público Fiscal y Ministerio Público de la Defensa de la Nación.",["43/2026","44/2026","45/2026"],47,
 "3,0,0,0 1,0,0,0 2,0,0,0 2,0,0,1 1,0,0,0 2,0,0,0 17,0,0,4 20,0,0,1 0,0,0,1 2,0,0,0 2,0,0,0 1,0,0,0 1,0,0,1 10,0,0,0"),
(2767,"04-06-2026",5,"EN GENERAL Y EN PARTICULAR","Acuerdo para designar a la Juez del Tribunal Federal de Juicio de Santa Fe a Emilio Rosatti.",["90/2026"],1,
 "3,0,0,0 1,0,0,0 0,2,0,0 2,0,0,1 1,0,0,0 0,2,0,0 1,16,0,4 20,0,0,1 0,0,0,1 2,0,0,0 2,0,0,0 1,0,0,0 1,0,0,1 10,0,0,0"),
(2768,"04-06-2026",6,"EN GENERAL Y EN PARTICULAR","Acuerdo para designaciones en el Poder Judicial, Ministerio Público Fiscal y Ministerio Público de la Defensa de la Nación.",["91/2026","92/2026","93/2026"],11,
 "3,0,0,0 1,0,0,0 2,0,0,0 2,0,0,1 1,0,0,0 2,0,0,0 17,0,0,4 20,0,0,1 0,0,0,1 2,0,0,0 2,0,0,0 1,0,0,0 1,0,0,1 10,0,0,0"),
(2769,"04-06-2026",7,"EN GENERAL Y EN PARTICULAR","Acuerdo para designar a la Jueza de Cámara del Tribunal Oral en lo Criminal Federal N°3 de La Plata a María Verónica Michelli.",["112/2026"],1,
 "3,0,0,0 1,0,0,0 2,0,0,0 2,0,0,1 1,0,0,0 2,0,0,0 17,0,0,4 1,18,1,1 0,0,0,1 2,0,0,0 2,0,0,0 1,0,0,0 1,0,0,1 9,0,1,0"),
(2770,"04-06-2026",8,"EN GENERAL Y EN PARTICULAR","Acuerdo de conciliación con acreedores de títulos de deuda.",["102/2026"],1,
 "3,0,0,0 1,0,0,0 0,2,0,0 2,0,0,1 1,0,0,0 0,2,0,0 0,16,0,5 20,0,0,1 0,0,0,1 0,2,0,0 2,0,0,0 1,0,0,0 1,0,0,1 9,0,0,1"),
(2771,"04-06-2026",9,"EN GENERAL Y EN PARTICULAR","Creación de una nueva sala en la Cámara Federal de Apelaciones de Mar del Plata. Reorganización y ampliación de la Cámara Federal de Apelaciones de Tucumán.",["103/2026","105/2026"],2,
 "3,0,0,0 1,0,0,0 2,0,0,0 1,0,0,2 1,0,0,0 2,0,0,0 16,0,0,5 20,0,0,1 0,0,0,1 2,0,0,0 2,0,0,0 1,0,0,0 1,0,0,1 9,0,0,1"),
(2691,"14-05-2026",4,"EN GENERAL Y EN PARTICULAR","Prórroga por cinco años del mandato de Carlos Alberto Mahiques como vocal de la Cámara Federal de Casación Penal.",["17/2026"],1,
 "3,0,0,0 0,0,0,1 2,0,0,0 2,0,0,1 1,0,0,0 2,0,0,0 9,11,0,1 21,0,0,0 1,0,0,0 2,0,0,0 2,0,0,0 1,0,0,0 2,0,0,0 10,0,0,0"),
]
actas = []
for (i, f, n, t, ti, ods, nods, c) in A:
    grupos = c.split()
    assert len(grupos) == 14, (i, len(grupos))
    pb = {}
    for b, g in zip(B, grupos):
        a_, n_, b_, x_ = map(int, g.split(","))
        pb[b] = {"a": a_, "n": n_, "b": b_, "x": x_}
    tot = sum(sum(v.values()) for v in pb.values())
    assert tot == 72, (i, tot)
    actas.append({"id": i, "fecha": f, "nro_acta": str(n), "titulo": ti, "tipo": t, "resultado": "AFIRMATIVO",
                  "mayoria": "SIMPLE", "ods": [{"nro": int(o.split('/')[0]), "anio": 2026} for o in ods],
                  "n_ods": nods, "por_bloque": pb})
salida = {"anio": 2026, "actualizado": "15-10-2026", "fuente": "https://www.senado.gob.ar/votaciones/actas", "actas": actas}
dest = sys.argv[1]
os.makedirs(os.path.dirname(dest), exist_ok=True)
json.dump(salida, open(dest, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok", len(actas))
