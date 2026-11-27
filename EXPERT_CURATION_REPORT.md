# Preauditoría técnica y curación experta · Fase 02-B

Se inspeccionaron los 64 candidatos SFT y los 32 casos de CyberBench originales. El informe individual fija ID, hash de contenido, categoría, idioma, dificultad, premisa, etiqueta, referencias del catálogo, resultado automático y recomendación. Las dos traducciones de cada escenario conservan su enlace y contienen observaciones pertinentes al idioma. Las notas asisten al revisor y conservan 96 estados pendientes. Los archivos originales se mantuvieron byte por byte.

| Hallazgo | Decisión de curación |
|---|---|
| `pilot-001` muestra construcción de una consulta pero falta el sumidero | Pedir evidencia de ejecución o ajustar el lenguaje a riesgo condicional |
| `pilot-006` presenta mantenimiento alegado como evidencia contradictoria | Distinguir explicación plausible de evidencia que la contradice |
| 28 casos de CyberBench comparten una respuesta genérica | Redactar razones específicas y adjudicarlas; conservar la suite de desarrollo separada |
| Dificultad fundamental/intermedia y evidencia en inglés en parte de los casos ES | Validar razonamiento, traducción y terminología en cada revisión |
| Identificador CVE deliberadamente ficticio en un caso | Conservar la incertidumbre sobre fuentes incompletas y evitar afirmaciones de existencia global |

La curación mecánica aceptó 64 SFT y 32 casos de CyberBench para revisión. Los 54 casos reservados en la revisión SFT incluyen 10 legacy, 32 CyberBench y 12 CodeBench. Cero solapamientos detectados por los controles existentes. Cero registros aprobados por expertos, cero elegibles, cero rechazos y cuarentenas reales. Los 12 casos de CodeBench se cuentan como desarrollo nuevo, por separado de los 96 preauditados.

La interfaz localhost permite seleccionar registros, filtrar, consultar fuentes y licencia, leer las notas y guardar comentarios, propuestas o decisiones individuales firmadas. Una propuesta queda como evidencia junto a la versión original. Para promoverla, materializa una nueva revisión con su propia procedencia y firma. Se verificaron el flujo HTTP local, rechazo de origen externo y exportación de prueba. Los fixtures se quedaron en directorios temporales.

Pilot A sigue pendiente de decisiones humanas. Pilot B aspira a otros 250 candidatos si existe material revisable y autorizado. Pilot C exige 500–1,000 aprobados con diversidad, profundidad y evaluación independiente. Esta fase evita llenar ese déficit con duplicados o salidas de asistentes. El único insumo de software nuevo es la adquisición de referencia de un archivo SQLite sin muestras derivadas.

Informe por registro: [candidate_preaudit.jsonl](audits/phase02b/candidate_preaudit.jsonl). Procedimiento: [revisión humana](DATASET_REVIEW_GUIDE.md).
