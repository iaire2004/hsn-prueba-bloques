# Páginas por bloque — Prosecretaría Parlamentaria

Una página informativa por bloque, sólo con los datos de ese bloque. Se publican en
`https://prosecretaria-parlamentaria-hsn.github.io/<bloque>/` (por ejemplo `/frente-pro/`).

## Piezas
- `scripts/generar_bloques.py` — arma las 14 páginas desde los datos del sistema legislativo.
- `scripts/plantilla_bloque.html` — diseño de la página (identidad sin logo, Poppins embebida).
- `scripts/scraper_votaciones.py` — lee las actas de votación del Senado (sólo votaciones en general) y guarda `data/votaciones.json`. Incremental, con pausa de 3 s, tope de 25 detalles por corrida y corte si el sitio limita el acceso.
- `.github/workflows/actualizar-bloques.yml` — corre 40 minutos después de cada actualización del sistema (12:40 y 01:40 UTC).
- `tests/` — prueba del lector de votaciones y generador de datos de desarrollo.

## Uso local
    HSN_SOURCE=ruta/al/repo/hsn-sistema-legislativo python scripts/generar_bloques.py [slug]

## Reglas vigentes de atribución (los 14 bloques)
Las aplica `generar_bloques.py` (función `bloques_de_proyecto`) al generar cada página.

1. **Autor**: el que nombra la carátula (el prefijo antes de los dos puntos), no el orden de la columna AUTOR del Excel.
2. **Uno o varios autores**: con un solo autor el proyecto es de ese senador y de su bloque. Con dos o más cuenta para
   cada senador y para el bloque de cada uno, una sola vez por bloque. Con «y otros» cuentan solo los nombrados.
   «Varios senadores» queda como estaba.
3. **Bloque**: el bloque actual del senador según `senadores.json`, calculado al generar (no se usa el bloque
   registrado al presentar). El proyecto sigue a su senador: si cambia de bloque, sus proyectos pasan al nuevo
   (ejemplo: Arce, incorporado a Movimiento por Misiones el 18-08-2026, tiene todos sus proyectos en ese bloque).
4. **Año**: el del número de expediente (campo `anio`), nunca el de la fecha de ingreso.
5. **Estado**: el Excel de trazabilidad es la fuente oficial. Aprobados: Boletín de Novedades y, si no trae la
   aprobación, el código AP del Excel (`USAR_AP_TRAZABILIDAD`).
6. **Reunión de comisión**: se infiere si el proyecto tiene orden del día (Ayuda Memoria o planilla), fecha de dictamen
   o fue aprobado desde una orden del día; se muestra sin fecha. Esos casos se listan en
   `data/reuniones_a_rastrear.json`.
7. **Por caducar**: proyectos de ley de 2025 de senadores vigentes, sin archivo, sin ley y sin media sanción. Un autor
   que ya no es senador no aporta bloque; si todos los autores del prefijo dejaron el Senado, cuenta para los demás
   firmantes vigentes; si el prefijo mezcla ex senadores y vigentes, cuentan solo los vigentes. Las tarjetas indican
   «Autor/a con mandato cumplido» y el encabezado muestra el desglose.
8. **Más de un bloque**: un proyecto puede figurar en varios bloques; cada tarjeta muestra «También figura en: [Bloque]».

Los datos (`autores_caratula`, `firmantes_trazabilidad`) los genera `scripts/aplicar_trazabilidad_csv.py` del repo del
sistema legislativo; `bloques_caratula` se guarda allá por compatibilidad, pero esta generación no depende de él.
