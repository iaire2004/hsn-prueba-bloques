import sys, os
from types import SimpleNamespace
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import generar_bloques as gb

UCR = "UCR - UNIÓN CÍVICA RADICAL"
MIS = "MOVIMIENTO POR MISIONES"
# senadores VIGENTES con su bloque ACTUAL (senadores.json)
VIG = {"FAMA, FLAVIO SERGIO": UCR, "ABAD, MAXIMILIANO": UCR, "ROJAS DECUT, SONIA ELIZABETH": MIS,
       "ARCE, CARLOS OMAR": MIS, "VALENZUELA, MERCEDES GABRIELA": UCR}
senador_de = lambda a: (a, {"bloque": VIG[a]}) if a in VIG else None

# año del número, no de la fecha
assert gb.anio_de({"anio": 2025, "fecha": "15/01/2026"}) == 2025
assert gb.anio_de({"fecha": "15/01/2026"}) == 2026

# prefijo con un solo autor: su bloque actual; el primer firmante que no figura en el prefijo no cuenta
p = {"origen": "S", "anio": 2026, "autores": ["VALENZUELA, MERCEDES GABRIELA", "ROJAS DECUT, SONIA ELIZABETH"],
     "bloques": [UCR, MIS], "autores_caratula": ["ROJAS DECUT, SONIA ELIZABETH"], "bloques_caratula": [UCR]}
# ni bloques ni bloques_caratula guardados importan: se recalcula con senadores.json
assert gb.bloques_de_proyecto(p, senador_de) == [MIS]
assert not gb.pertenece_a_bloque(p, UCR, senador_de)
assert gb.pertenece_a_bloque(p, "Movimiento por Misiones", senador_de)

# cambio de bloque: Arce se incorporó a Movimiento por Misiones el 18-08-2026; un proyecto
# de marzo (registrado entonces en otro bloque) queda en su bloque ACTUAL
p_arce = {"origen": "S", "anio": 2026, "fecha": "02/03/2026", "autores": ["ARCE, CARLOS OMAR"],
          "bloques": ["LA LIBERTAD AVANZA"], "autores_caratula": ["ARCE, CARLOS OMAR"], "bloques_caratula": ["LA LIBERTAD AVANZA"]}
assert gb.bloques_de_proyecto(p_arce, senador_de) == [MIS]
assert not gb.pertenece_a_bloque(p_arce, "LA LIBERTAD AVANZA", senador_de)
VIG2 = dict(VIG, **{"ARCE, CARLOS OMAR": "LA LIBERTAD AVANZA"})  # si cambiara de nuevo, el proyecto lo sigue
assert gb.bloques_de_proyecto(p_arce, lambda a: (a, {"bloque": VIG2[a]}) if a in VIG2 else None) == ["LA LIBERTAD AVANZA"]

# dos autores del mismo bloque cuentan una vez; de bloques distintos, en ambos
p2 = {"origen": "S", "anio": 2026, "autores_caratula": ["FAMA, FLAVIO SERGIO", "ABAD, MAXIMILIANO"]}
assert gb.bloques_de_proyecto(p2, senador_de) == [UCR]
p2b = {"origen": "S", "anio": 2026, "autores_caratula": ["FAMA, FLAVIO SERGIO", "ARCE, CARLOS OMAR"]}
assert gb.bloques_de_proyecto(p2b, senador_de) == [UCR, MIS]

# sin los campos nuevos: bloque actual del primer autor
p3 = {"origen": "S", "anio": 2026, "autores": ["ABAD, MAXIMILIANO", "C, D"]}
assert gb.bloques_de_proyecto(p3, senador_de) == [UCR]

# ex senadores: un autor que ya no es senador no aporta bloque (el mixto cuenta sólo a los vigentes)
p4 = {"origen": "S", "anio": 2025, "autores_caratula": ["FAMA, FLAVIO SERGIO", "DE ANGELI, ALFREDO LUIS"]}
assert gb.bloques_de_proyecto(p4, senador_de) == [UCR]
# prefijo sólo de ex senadores: cuenta para los firmantes vigentes
p5 = {"origen": "S", "anio": 2025, "autores_caratula": ["DE ANGELI, ALFREDO LUIS"],
      "autores": ["ABAD, MAXIMILIANO"], "coautores": ["ROJAS DECUT, SONIA ELIZABETH"], "firmantes_trazabilidad": ["FAMA, FLAVIO SERGIO"]}
assert gb.bloques_de_proyecto(p5, senador_de) == [UCR, MIS]
# sin ningún vigente: no cuenta para ningún bloque
assert gb.bloques_de_proyecto({"origen": "S", "anio": 2025, "autores_caratula": ["DE ANGELI, ALFREDO LUIS"], "autores": ["DE ANGELI, ALFREDO LUIS"]}, senador_de) == []
# otros orígenes no tienen bloque
assert gb.bloques_de_proyecto({"origen": "PE", "anio": 2026, "autores_caratula": ["FAMA, FLAVIO SERGIO"]}, senador_de) == []

# mandato cumplido: sólo con datos confirmados en senadores.json
sen = {"DE ANGELI, ALFREDO LUIS": {"vigente": False}, "FAMA, FLAVIO SERGIO": {"vigente": True}}
norm = lambda n: n.upper()
ctx = {"gw": SimpleNamespace(_norm_nombre=norm), "sen_todos": {k: (k, v) for k, v in sen.items()}, "autor_sin_dato": set(), "autor_por_apellido": set()}
pm = {"origen": "S", "anio": 2025, "nro": 1, "autores_caratula": ["FAMA, FLAVIO SERGIO", "DE ANGELI, ALFREDO LUIS", "NADIE, UNO"]}
assert gb.mandato_cumplido_de(ctx, pm) == ["Alfredo Luis De Angeli"]
assert ctx["autor_sin_dato"] == {("S-1/25", "NADIE, UNO")}

# aprobación: Boletín primero, AP de la trazabilidad si falta
assert gb.aprobacion_de({"badge_sancionado": {"fecha": "01/01/2026", "ley": "Ley 1"}})["ley"] == "Ley 1"
assert gb.aprobacion_de({"sanciones_trazabilidad": [{"codigo": "AP", "fecha": "27/08/2026"}, {"codigo": "AP", "fecha": "17/09/2026"}]})["fecha"] == "17/09/2026"
assert gb.aprobacion_de({"sanciones_trazabilidad": [{"codigo": "MO", "fecha": "27/08/2026"}]}) is None
print("ok")
