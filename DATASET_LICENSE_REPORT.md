# Derechos de adquisición y entrenamiento · Fase 02-B

La autorización efectiva usa el catálogo del track correspondiente, fijado por hash en cada paquete. Disponibilidad pública y aptitud técnica se registran por separado.

| Entrada | Acceso | Adquisición | Procesamiento | SFT | Redistribuir dataset o pesos | Atribución y límites |
|---|---|---|---|---|---|---|
| SQLite `src/complete.c` en la revisión fijada | Público | Habilitada por SHA-256 | Análisis local de código fuente | Uso local autorizado por la política, sujeto a aprobar los registros | Deshabilitada por política de Rsec | Preservar procedencia y encabezado. El aviso del editor cubre el código entregable y excluye inferencias sobre scripts de build o terceros |
| Ejemplos de documentación Python | Público | Pendiente del ítem y revisión | Pendiente del ítem | Pendiente | Pendiente | PSF-2.0 y 0BSD para ejemplos de código que cumplen el alcance indicado por PSF. No extiende 0BSD a toda la prosa |
| Aportes de programación del propietario o colaboradores | Privado hasta autorización | Aporte explícito | Pendiente de procedencia | Pendiente de autorización por escrito | Pendiente por separado | Identificar autor, alcance y autorización de pesos antes de publicar |
| CVE previamente fijados | Público | Tres archivos | Solo índices de referencia | Deshabilitado | Deshabilitado | Preservar identidad CVE y revisión |
| CodeBench y CyberBench desarrollo | Público | Incluido en repositorio | Evaluación y regresión | Reservado | Código y datos originales de desarrollo según licencia de repositorio | Conservar el aislamiento del entrenamiento |

SQLite se descargó como texto a través del conector autorizado. Sus 12,269 bytes coinciden con el blob de origen y su caché se verificó con el adaptador registrado. El contenido se conservó en `data/raw/software/`, ignorado por Git. El informe solo versiona la evidencia de adquisición. No se generaron ejemplos SFT a partir del archivo. Las políticas originales de ciberseguridad se conservan en el catálogo anterior.

Fuentes primarias: [SQLite Copyright](https://sqlite.org/copyright.html), [archivo exacto de SQLite](https://github.com/sqlite/sqlite/blob/95170adc372e2a3d7ca664c3f3673a5258b0dd78/src/complete.c), [History and License de Python](https://docs.python.org/3/license.html). Evidencia: [software_acquisition.json](audits/phase02b/software_acquisition.json).

Los datos privados y las salidas de asistentes siguen excluidos de la ingesta automática. Una licencia de repositorio no se aplica por defecto a los datasets adjuntos ni a los pesos derivados. Verifica el alcance por ítem antes de importar repositorios completos.
