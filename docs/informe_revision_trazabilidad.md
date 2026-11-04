# Informe de revisión de trazabilidad (14 bloques, 2025 y 2026)

Fecha de la revisión: 21-10-2026. Estado: **sin publicar**. Ambos repos tienen los cambios en la rama `revision-trazabilidad`; `main` no se tocó y no se disparó ningún workflow. La publicación espera la instrucción «publicar».

## 1. Causa real de los proyectos ausentes en la fuente

La hipótesis de la ventana de 30 días **no es la causa de los 21 proyectos de ley de 2026 ni de los 15 de 2025**. Esos 36 expedientes (S-3 a S-34/25 y S-3 a S-273/26, todos proyectos de ley de marzo) faltaban porque la clave de deduplicación era `(nro, anio, tipo)` e **ignoraba el origen**. La numeración es independiente por origen (S, PE, CD, OV, P): por ejemplo, el S-94/26 (proyecto de ley de Abad) tiene el mismo número, año y tipo que el PE-94/26 (mensaje del Poder Ejecutivo y proyecto de ley, 13-04-2026). El primero que llegaba se guardaba y el segundo se descartaba en silencio, tanto en `importar_proyectos_xlsx.py` (`claves_vistas`) como en `scraper_proyectos.py` (`clave_proyecto`, `claves_existentes` y el filtro de `pendientes`) y en `importar_aprobados.py`. En los 36 casos ya existía un proyecto de ley de otro origen con el mismo número: 25 proyectos en revisión de Diputados (CD) y 11 mensajes del Poder Ejecutivo (PE).

Los 4 expedientes restantes de 2025 (S-2202 y S-2203, comunicaciones de cuestión de privilegio, y S-2204 y S-2205, proyectos de declaración, todos ingresados el 27-02-2026) sí responden a la hipótesis original: no estaban en la exportación con la que se sembró el archivo y quedaron fuera de la ventana del scraper. El S-1693/26 existía en la fuente pero sin autor (el scraper no levantó los firmantes) y se completó.

Corrección: la clave ahora incluye el origen en `scraper_proyectos.py`, `importar_proyectos_xlsx.py` e `importar_aprobados.py`, de modo que el scraper no vuelve a perder expedientes por este motivo. Además se agregó un chequeo de huecos al final del scraper (`chequear_huecos`): registra en el log, por año, la cantidad de expedientes de origen S, el número más alto visto y los que faltan entre los últimos 200.

## 2. Resumen por bloque (2026)

«Antes» es la generación con el código y los datos anteriores; «después» es la generación con los datos corregidos y las reglas nuevas. Entran y salen se refiere a los proyectos de 2026 de la lista de Proyectos 2026 de cada bloque; los /25 que salen de 2026 se cuentan aparte.

| Bloque | Proyectos 2026 antes | después | Con reunión antes | después | Con orden del día antes | después | Aprobados antes | después | Por caducar antes | después | Entran | Salen | /25 que salen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Convicción Federal | 101 | 101 | 14 | 19 | 6 | 5 | 6 | 7 | 22 | 42 | 2 | 2 | 0 |
| Despierta Chubut | 31 | 29 | 7 | 6 | 5 | 4 | 0 | 0 | 6 | 9 | 0 | 2 | 0 |
| Frente Cívico por Santiago | 23 | 25 | 4 | 4 | 3 | 3 | 0 | 0 | 1 | 1 | 2 | 0 | 0 |
| Frente PRO | 34 | 36 | 3 | 7 | 1 | 2 | 5 | 5 | 19 | 19 | 4 | 0 | 2 |
| Independencia | 69 | 69 | 12 | 14 | 5 | 5 | 5 | 7 | 75 | 74 | 0 | 0 | 0 |
| Justicia Social Federal | 45 | 45 | 6 | 6 | 0 | 0 | 0 | 0 | 13 | 23 | 0 | 0 | 0 |
| Justicialista | 735 | 716 | 51 | 56 | 12 | 11 | 10 | 12 | 121 | 161 | 21 | 3 | 37 |
| La Libertad Avanza | 169 | 158 | 25 | 43 | 13 | 11 | 26 | 31 | 30 | 35 | 3 | 1 | 13 |
| La Neuquinidad | 36 | 36 | 2 | 2 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 |
| Movere por Santa Cruz | 39 | 40 | 5 | 7 | 3 | 3 | 2 | 6 | 28 | 28 | 3 | 0 | 2 |
| Movimiento por Misiones | 61 | 61 | 14 | 15 | 4 | 5 | 1 | 2 | 4 | 5 | 1 | 1 | 0 |
| Primero los Salteños | 44 | 45 | 4 | 5 | 1 | 2 | 0 | 1 | 0 | 0 | 1 | 0 | 0 |
| Provincias Unidas | 7 | 8 | 1 | 2 | 0 | 0 | 0 | 1 | 6 | 8 | 1 | 0 | 0 |
| UCR - Unión Cívica Radical | 258 | 259 | 25 | 36 | 14 | 13 | 19 | 22 | 49 | 55 | 12 | 1 | 10 |

«Aprobados» es la lista de proyectos aprobados por el Senado en sesiones de 2026 (cualquier año de presentación). Los cambios se explican por la atribución por carátula, por los 40 expedientes agregados y por la aprobación según la planilla (punto 8).

## 3. Proyectos que cambian de bloque o se cuentan en más de un bloque

| Proyecto | Bloques antes | Bloques ahora | Observación |
|---|---|---|---|
| S-7/26 | Movimiento por Misiones | UCR - Unión Cívica Radical | cambia de bloque |
| S-115/26 | UCR - Unión Cívica Radical | Movimiento por Misiones | cambia de bloque |
| S-252/26 | Convicción Federal | Convicción Federal, Justicialista | suma bloque |
| S-257/26 | Despierta Chubut | UCR - Unión Cívica Radical | cambia de bloque |
| S-261/26 | Justicialista | Movere por Santa Cruz | cambia de bloque |
| S-313/26 | Convicción Federal | Justicialista | cambia de bloque |
| S-381/26 | Justicialista | Justicialista, UCR - Unión Cívica Radical | suma bloque |
| S-397/26 | UCR - Unión Cívica Radical | Frente PRO, UCR - Unión Cívica Radical | suma bloque |
| S-419/26 | La Libertad Avanza | Frente PRO | cambia de bloque |
| S-447/26 | Convicción Federal | Justicialista | cambia de bloque |
| S-456/26 | Movere por Santa Cruz | Movere por Santa Cruz, UCR - Unión Cívica Radical | suma bloque |
| S-465/26 | Frente PRO | Frente PRO, UCR - Unión Cívica Radical | suma bloque |
| S-596/26 | Justicialista | Frente PRO, Justicialista | suma bloque |
| S-633/26 | La Libertad Avanza | La Libertad Avanza, Movere por Santa Cruz | suma bloque |
| S-727/26 | Justicialista | Convicción Federal, Justicialista | suma bloque |
| S-808/26 | Despierta Chubut | Primero los Salteños | cambia de bloque |
| S-897/26 | Justicialista | La Libertad Avanza, Movere por Santa Cruz | cambia de bloque |
| S-1090/26 | Justicialista | Justicialista, UCR - Unión Cívica Radical | suma bloque |
| S-1102/26 | UCR - Unión Cívica Radical | Frente PRO, UCR - Unión Cívica Radical | suma bloque |
| S-1103/26 | UCR - Unión Cívica Radical | Justicialista, UCR - Unión Cívica Radical | suma bloque |
| S-1140/26 | Justicialista | Convicción Federal | cambia de bloque |
| S-1292/26 | Movere por Santa Cruz | Justicialista, Movere por Santa Cruz | suma bloque |
| S-1385/26 | UCR - Unión Cívica Radical | Frente Cívico por Santiago, UCR - Unión Cívica Radical | suma bloque |
| S-1464/26 | Movere por Santa Cruz | La Libertad Avanza, Movere por Santa Cruz | suma bloque |
| S-1554/26 | Movere por Santa Cruz | Frente Cívico por Santiago, Movere por Santa Cruz | suma bloque |
| S-1618/26 | Frente Cívico por Santiago | Frente Cívico por Santiago, Justicialista | suma bloque |
| S-1738/26 | La Libertad Avanza | La Libertad Avanza, UCR - Unión Cívica Radical | suma bloque |

Total: 27 proyectos. Los que antes no estaban en ningún bloque (los 40 agregados y los de carátula con senadores de otro bloque) figuran como «entran» en el punto 2 y los agregados en el punto 4.

### Proyectos /25 que salen de 2026

Son los proyectos numerados /25 con fecha de ingreso de enero o febrero de 2026 que antes se contaban como de 2026. Ahora el año es el del número: salen de proyectos, tarjetas, tipos, evolución mensual, comisiones, senadores, síntesis y modo pantalla de 2026, y los proyectos de ley pasan a evaluarse para «Por caducar».

Total: 64 proyectos /25 (PD 31, CO 6, PL 15, PC 12): S-2125/25, S-2126/25, S-2127/25, S-2128/25, S-2129/25, S-2130/25, S-2131/25, S-2132/25, S-2133/25, S-2134/25, S-2135/25, S-2136/25, S-2137/25, S-2138/25, S-2139/25, S-2140/25, S-2141/25, S-2142/25, S-2143/25, S-2144/25, S-2145/25, S-2146/25, S-2147/25, S-2148/25, S-2149/25, S-2150/25, S-2151/25, S-2152/25, S-2153/25, S-2154/25, S-2155/25, S-2156/25, S-2158/25, S-2159/25, S-2160/25, S-2161/25, S-2162/25, S-2163/25, S-2164/25, S-2165/25, S-2166/25, S-2167/25, S-2168/25, S-2169/25, S-2170/25, S-2171/25, S-2175/25, S-2176/25, S-2177/25, S-2178/25, S-2179/25, S-2180/25, S-2181/25, S-2184/25, S-2189/25, S-2190/25, S-2192/25, S-2193/25, S-2194/25, S-2196/25, S-2197/25, S-2198/25, S-2199/25, S-2200/25.

## 4. Proyectos agregados a la fuente

40 expedientes de origen S (21 de 2026 y 19 de 2025). Registros en `proyectos.json`: 4602 antes, 4642 después. Un registro completado (S-1693/26). Ningún registro ni campo se perdió (el script lo verifica con aserciones). Desglose por año y tipo: 2025-CO: +2, 2025-PD: +2, 2025-PL: +15, 2026-PL: +21.

| Número | Año | Tipo | Autor/es (carátula) | Bloque/s |
|---|---|---|---|---|
| S-273/26 | 2026 | PL | Soria, Martin Ignacio | Justicialista |
| S-271/26 | 2026 | PL | Capitanich, Jorge Milton | Justicialista |
| S-223/26 | 2026 | PL | Capitanich, Jorge Milton, Bahl, Adán Humberto | Justicialista |
| S-193/26 | 2026 | PL | Fernández Sagasti, Anabel | Justicialista |
| S-186/26 | 2026 | PL | Fernández Sagasti, Anabel | Justicialista |
| S-185/26 | 2026 | PL | Fernández Sagasti, Anabel | Justicialista |
| S-100/26 | 2026 | PL | Alvarez Rivero, Carmen | La Libertad Avanza |
| S-98/26 | 2026 | PL | Abad, Maximiliano | Ucr - Unión Cívica Radical |
| S-97/26 | 2026 | PL | Abad, Maximiliano | Ucr - Unión Cívica Radical |
| S-95/26 | 2026 | PL | Abad, Maximiliano | Ucr - Unión Cívica Radical |
| S-94/26 | 2026 | PL | Abad, Maximiliano | Ucr - Unión Cívica Radical |
| S-17/26 | 2026 | PL | Capitanich, Jorge Milton | Justicialista |
| S-16/26 | 2026 | PL | Capitanich, Jorge Milton | Justicialista |
| S-15/26 | 2026 | PL | Capitanich, Jorge Milton | Justicialista |
| S-14/26 | 2026 | PL | Capitanich, Jorge Milton | Justicialista |
| S-13/26 | 2026 | PL | Capitanich, Jorge Milton | Justicialista |
| S-12/26 | 2026 | PL | Capitanich, Jorge Milton | Justicialista |
| S-11/26 | 2026 | PL | Capitanich, Jorge Milton | Justicialista |
| S-10/26 | 2026 | PL | Capitanich, Jorge Milton | Justicialista |
| S-9/26 | 2026 | PL | Capitanich, Jorge Milton | Justicialista |
| S-3/26 | 2026 | PL | Vigo, Alejandra María, Espínola, Carlos Mauricio | Provincias Unidas |
| S-2205/25 | 2025 | PD | Fama, Flavio Sergio | Ucr - Unión Cívica Radical |
| S-2204/25 | 2025 | PD | Schneider, Silvana Lorena | Ucr - Unión Cívica Radical |
| S-2203/25 | 2025 | CO | Linares, Carlos Alberto | Justicialista |
| S-2202/25 | 2025 | CO | Rejal, Jesús Fernando | Justicia Social Federal |
| S-34/25 | 2025 | PL | García Larraburu, Silvina Marcela | Unidad Ciudadana |
| S-33/25 | 2025 | PL | García Larraburu, Silvina Marcela | Unidad Ciudadana |
| S-31/25 | 2025 | PL | García Larraburu, Silvina Marcela | Unidad Ciudadana |
| S-30/25 | 2025 | PL | Rodas, Antonio José | Frente Nacional Y Popular |
| S-24/25 | 2025 | PL | Rodas, Antonio José | Frente Nacional Y Popular |
| S-23/25 | 2025 | PL | Rodas, Antonio José | Frente Nacional Y Popular |
| S-22/25 | 2025 | PL | Rodas, Antonio José | Frente Nacional Y Popular |
| S-21/25 | 2025 | PL | Rodas, Antonio José | Frente Nacional Y Popular |
| S-15/25 | 2025 | PL | Rodas, Antonio José | Frente Nacional Y Popular |
| S-8/25 | 2025 | PL | Sapag, Silvia Estela | Unidad Ciudadana |
| S-7/25 | 2025 | PL | Sapag, Silvia Estela | Unidad Ciudadana |
| S-6/25 | 2025 | PL | Sapag, Silvia Estela | Unidad Ciudadana |
| S-5/25 | 2025 | PL | Sapag, Silvia Estela | Unidad Ciudadana |
| S-4/25 | 2025 | PL | Sapag, Silvia Estela | Unidad Ciudadana |
| S-3/25 | 2025 | PL | Sapag, Silvia Estela | Unidad Ciudadana |

## 5. Cambios de estado por conciliación con la planilla

Se compararon archivado, fecha de archivo, ley, fecha de ingreso y comisiones de todos los expedientes S de 2025 y 2026 que ya estaban en la fuente. Solo difirieron dos expedientes (el CSV manda):

| Expediente | Campo | Valor anterior | Valor nuevo |
|---|---|---|---|
| S-160/26 PD | archivado | False | True |
| S-160/26 PD | fecha_archivo | None | 16-10-2026 |
| S-1311/25 PD | archivado | False | True |
| S-1311/25 PD | fecha_archivo | None | 16-10-2026 |

Las comisiones no difieren: se compararon ignorando el orden y el marcador «Solo para conocimiento» que agrega el scraper (la planilla no lo trae; por eso S-624/26 sigue como «conocimiento»). Ley, fecha de ingreso y tipo coinciden en todos.

## 6. Proyectos que siguen sin bloque y casos sin autoría por carátula

- **35 proyectos de 2025** (13 de ley, 20 de declaración, 2 de comunicación) son del exsenador Alfredo Luis De Angeli: figura en `senadores.json` como no vigente y sin bloque, así que su bloque es «Sin datos». Sus proyectos de ley entran en «Por caducar» del bloque de los firmantes vigentes que los acompañan; los demás tipos no cuentan para ningún bloque.
- 227 proyectos de ley de 2025 tienen todos los autores del prefijo fuera del Senado. Por decisión tomada en la revisión, cuentan para el bloque de los demás firmantes que siguen siendo senadores vigentes (los de ley, en «Por caducar»); si no hay ningún firmante vigente, no cuentan para ningún bloque. Para eso se guarda `firmantes_trazabilidad` (todos los firmantes de la planilla) en 938 registros.
- Sin prefijo de autor en la carátula (no se calcula autoría; se usa el comportamiento anterior): S-1650/25 PC, S-668/25 CO, S-286/25 PC.
- «Varios senadores» (sin cambios): S-112/26, S-1431/25.
- Registros de origen S de 2026 que no están en la planilla (comunicaciones de comisiones y comunicaciones de senadores sin prefijo de autor, como S-1534, S-1406, S-1398, S-1388, S-1751, S-1684, S-1617 y S-1499): siguen atribuidos como antes, por el bloque de su primer firmante.

## 7. ¿La corrida automática del repo de datos pisaría alguna corrección?

- `scraper_proyectos.py` (workflow `actualizar.yml`, franja de las 22:00): no toca `autores_caratula`, `bloques_caratula`, `od_trazabilidad`, `fecha_dictamen` ni `sanciones_trazabilidad`. Para los expedientes nuevos que raspa calcula `autores_caratula` y `bloques_caratula` con la misma función.
- `revisar_expedientes_abiertos` re-visita hasta 200 expedientes por corrida que no estén archivados ni sancionados. Sobrescribe `comisiones` cuando el sitio devuelve giros (con el marcador «Solo para conocimiento»: es el formato que ya tenían) y solo reemplaza archivo, caducidad y ley cuando el sitio trae un valor. Los dos expedientes archivados por conciliación (S-160/26 y S-1311/25) dejan de ser «abiertos» y no se re-visitan. Los 40 agregados no tienen `_ultima_revision`, así que son los primeros en re-visitarse: sus comisiones se reemplazarán por las del sitio, que son las mismas. No hay riesgo de que se pierdan las correcciones.
- `importar_aprobados.py` e `importar_proyectos_xlsx.py` no están en el workflow (son manuales). El primero pisaría archivo y ley con los xlsx de aprobados si se corriera; el segundo reemplaza todo el archivo. Ambos ya usan la clave con origen.
- `generar_web.py` ahora no embebe en la página principal los campos nuevos (solo los usan las páginas por bloque), de modo que el HTML principal crece solo por los 40 registros nuevos (unos 30 KB).

## 8. Decisiones que conviene revisar

1. **Aprobaciones según la planilla.** Hay 10 proyectos de 2026 y 3 de 2025 que la planilla marca como aprobados por el Senado (código AP, sesiones del 27-08-2026 y 17-09-2026) y que el Boletín de Novedades (`sanciones.json`, que se carga a mano; su última sesión cargada es la del 27-08-2026) no incluye: S-3, S-361, S-809, S-916, S-1035, S-1144, S-1239 y S-1246/26 (sesión del 17-09-2026) y S-252 y S-308/26 (sesión del 27-08-2026). Para que el cruce con la planilla dé cero diferencias, `generar_bloques.py` usa el AP de la planilla cuando el Boletín no lo tiene (constante `USAR_AP_TRAZABILIDAD`; en `False` vuelve al comportamiento anterior). Con eso también salen de «Por caducar» los proyectos de ley de 2025 con AP (media sanción): S-1271, S-1419 y S-1861/25. Afecta la pestaña Seguimiento (lista de aprobados) y los conteos.
2. **Atribución en Seguimiento.** Las órdenes del día, preferencias y aprobados usan la misma atribución por carátula que Proyectos y Por caducar (si no, un proyecto contaría para un bloque en una pestaña y para otro en la otra). El diseño de la pestaña no cambia.
3. **Decisiones tomadas tras la primera revisión.** (a) Los proyectos de ley de 2025 cuyo prefijo nombra solo a ex senadores se incluyen en «Por caducar» del bloque de los firmantes vigentes (antes quedaban fuera de todo bloque: S-556, S-557, S-1003, S-1226, S-1255, S-1256 y S-1733/25 en Justicialista, entre otros). (b) Los proyectos con autores de varios bloques siguen contando en cada uno de ellos.
4. **Textos de la página.** Se actualizaron las notas que decían «bloque de su primer autor» y se agregaron en «Cómo lo hacemos» la regla de atribución y la de reunión de comisión inferida.

## 9. Reunión de comisión inferida por orden del día

Un proyecto figura «con reunión de comisión» si la agenda registra una reunión realizada o, si no, si tiene orden del día (Ayuda Memoria o planilla), fecha de dictamen o fue aprobado a partir de una orden del día. Sin fecha de reunión, la tarjeta dice «Reunión de comisión», sin fecha. En la UCR pasan a tenerla S-1031, S-612, S-556, S-545, S-522, S-457, S-242 y S-227/26 (verificado). `data/reuniones_a_rastrear.json` (repo de la web) lista 51 proyectos de todos los bloques, con su orden del día y fecha de dictamen, para rastrear después en qué reunión se trataron.

## 10. S-96/26 (ley y enviado a Diputados)

Está en la página de la UCR (autor: Abad; Juri firma pero no figura en el prefijo). En la lista de Proyectos 2026 aparece **una sola tarjeta** con las etiquetas «Reunión de comisión · 19-05-2026», «Aprobado por el Senado», «Ley» y «Enviado a Diputados»; también figura una vez en la lista de aprobados (04-06-2026). **No hay doble conteo de proyecto**: cuenta 1 en el total (259) y 1 en cada categoría de «Qué pasó» (aprobado, ley y enviado a Diputados), porque esas categorías se superponen por diseño. En la síntesis solo se cuenta dentro de los aprobados del bloque. No se modificó nada. Las etiquetas son compatibles con una secuencia normal: el Senado lo aprobó y lo giró a Diputados, y después se sancionó como ley (27822).

## 11. Verificaciones

1. **Generación y pruebas.** Los 14 bloques se generaron en carpeta temporal con `HSN_SOURCE` apuntando al repo de datos corregido, sin errores. Pasan `tests/test_votaciones.py` y el nuevo `tests/test_atribucion.py`. Se recorrieron en navegador las 6 pestañas de las 14 páginas y no aparece «undefined», «NaN» ni «null» en pantalla; la tarjeta sin fecha de reunión muestra solo «Reunión de comisión».
2. **Cruce con la planilla 2026, por bloque.** Los proyectos de cada bloque coinciden uno a uno con los que salen del CSV por prefijo de carátula (excepto «Varios senadores»), y coinciden tipo, fecha, archivado, ley y aprobado: 0 faltantes y 0 diferencias de tipo, fecha, archivo, ley o aprobado. Sobran solo registros que no están en la planilla (punto 6) y el S-112/26 («Varios senadores»), todos justificados.
3. **Cruce con la planilla 2025 para «Por caducar».** Proyectos de ley /25 de senadores vigentes, sin archivo, sin ley y sin media sanción: 0 faltantes y 0 sobrantes en los 14 bloques; cada proyecto de la lista está en el Excel. (El cruce independiente no reconoce el apellido mal tipeado de S-2146/25, «CAPITANICH U OTROS», que el generador sí vincula.)
4. **Consistencia interna.** En los 14 bloques: total = suma por tipo = suma por mes = largo de la lista de Proyectos 2026; los contadores de «Qué pasó» (reunión, orden del día, preferencia, aprobado, ley, Diputados y «con movimiento») coinciden con la cantidad de proyectos de la lista con cada etiqueta, así que los botones coinciden con las listas filtradas. Sin identificadores duplicados.
5. **Antes y después.** Las páginas hoy publicadas se regeneraron con el código y los datos anteriores: coinciden con las publicadas salvo `fecha_reunion` de S-257/26 y S-525/26 (reuniones agregadas a la agenda desde la última corrida) y «datos al». La comparación con las páginas nuevas está en los puntos 2 y 3.
6. **Datos.** `generar_web.py` corre sin errores sobre una copia (4642 registros). `aplicar_trazabilidad_csv.py` es idempotente: la segunda corrida no produce cambios.