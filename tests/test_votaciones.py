import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import scraper_votaciones as sv

row = lambda i, nro, tit, tipo, extra="": f'''<tr role="row"><td class="sorting_1"><span style="display:none">20260924</span> 24/09/2026 </td>
<td class="ocultar">{nro}</td><td class="ocultar" style="max-width:300px"> {tit} <a onclick="mostrar({i})">Ver Expedientes</a>
<div id="mostrarOcultarDiv{i}" class="expedientesOcultos" style="display:none"><a onclick="ocultar({i})">Ocultar Expedientes</a><br>
<a href="/parlamentario/parlamentaria/ordenDelDiaResultadoLink/2026/367" target="_blank"> O.D. 367/2026 </a>{extra}</div></td>
<td class="ocultar">{tipo}</td><td class="ocultar"><span style="display:none">positivo</span> <div>AFIRMATIVO </div></td>
<td><a href="/votaciones/verActaVotacion/{i}"><button>descargar</button></a></td><td class="ocultar">SIMPLE</td>
<td><a href="/votaciones/detalleActa/{i}"><img></a></td><td><a href="https://youtu.be/x"><img></a></td></tr>'''
html = '<table id="actasTable"><thead><tr><th>x</th></tr></thead><tbody>' + \
    row(2829, 2, "Modificación de la Carta Orgánica del Banco Central.", "EN GENERAL") + \
    row(2830, 3, "Modificación de la Carta Orgánica del Banco Central. Artículo 1.", "EN PARTICULAR", ", Art. 1") + '</tbody></table>'
a = sv.parsear_listado(html)
assert len(a) == 2, a
assert a[0]["id"] == 2829 and a[0]["fecha"] == "24-09-2026" and a[0]["tipo"] == "EN GENERAL"
assert a[0]["titulo"] == "Modificación de la Carta Orgánica del Banco Central.", a[0]["titulo"]
assert a[0]["ods"] == [{"nro": 367, "anio": 2026}], a[0]["ods"]
assert a[0]["resultado"] == "AFIRMATIVO" and a[0]["mayoria"] == "SIMPLE", a[0]
assert a[1]["tipo"] == "EN PARTICULAR"

det = '''<p>Acta Nro: 2</p><span>24/09/2026 - 17:08</span><table id="tabla" class="table"><thead><tr><th>Foto</th></tr></thead><tbody>
<tr><td><a><img></a></td><td>MENDOZA, SANDRA MARIELA</td><td class="ocultar">CONVICCIÓN FEDERAL</td><td class="ocultar">TUCUMÁN</td><td><div>AFIRMATIVO</div></td></tr>
<tr><td></td><td>X, Y</td><td>FRENTE PRO</td><td>CHACO</td><td><div>ABSTENCIÓN</div></td></tr>
<tr><td></td><td>Z, W</td><td>JUSTICIALISTA</td><td>SALTA</td><td><div>AUSENTE</div></td></tr>
<tr><td></td><td>Q, R</td><td>JUSTICIALISTA</td><td>SALTA</td><td><div>NEGATIVO</div></td></tr></tbody></table>'''
hora, votos = sv.parsear_detalle(det)
assert hora == "17:08", hora
assert [v["voto"] for v in votos] == ["a", "b", "x", "n"], votos
assert votos[0]["bloque"] == "CONVICCIÓN FEDERAL" and votos[0]["provincia"] == "TUCUMÁN"
print("ok")
