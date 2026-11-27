# Programación e ingeniería de software en Rsec

Rsec se diseña como un asistente bilingüe que opera localmente. Ciberseguridad defensiva y programación son capacidades centrales. Comparten el ciclo de datos, entrenamiento y registro, y tienen suites de evaluación independientes. El modelo base fijado sigue siendo Qwen2.5-Coder-7B-Instruct. Su rendimiento y retención deben medirse.

## Datos

La [taxonomía de software](../configs/software_taxonomy.json) versión `software-1.0.0` cubre generación funcional, debugging, refactorización, arquitectura, frontend, backend, APIs, automatización, herramientas defensivas, bases de datos, testing, DevSecOps, CI/CD, análisis de repositorios, optimización, programación segura y documentación. Los 13 lenguajes configurados son categorías posibles. El alcance medido de cada release se declara por separado.

Los candidatos siguen Candidate v2, con `domain=software_engineering`, subcategoría, tipo de tarea, idioma, familia, revisión de origen y referencias. Para tareas de repositorio registra commit, archivos y relación con el problema original. Une en una familia sus versiones, alternativas y traducciones. Separa repositorios y orígenes cuando un conjunto tenga fragmentos del mismo proyecto. El catálogo de software es independiente para preservar los hashes de permisos de ciberseguridad.

```bash
rsec data sources --registry data/manifests/software_source_registry.json
rsec data download --registered --config configs/software_sources.yaml
rsec data curate --input data/interim/software-candidates.jsonl \
  --taxonomy configs/software_taxonomy.json \
  --registry data/manifests/software_source_registry.json \
  --version software-pilot-1 --output data/processed/software-pilot-1
```

`software-candidates.jsonl` será un archivo preparado y revisado localmente. Hay una revisión concreta de SQLite autorizada para el propósito local, con revisión de datos aún pendiente. Consulta los permisos y límites de redistribución en [el informe de derechos](../DATASET_LICENSE_REPORT.md).

## Entrenamiento mixto y replay

Los dos releases de entrada deben pasar la validación SFT v2. El mezclador comprueba el catálogo vigente de cada track y rechaza familias vinculadas entre ambos, duplicados y coincidencias entre entrenamiento y datos reservados. Las reservas públicas incluyen los fixtures de Fase 01, CyberBench y CodeBench. Pasa las suites privadas desde el entorno autorizado según la política de evaluación.

El orden y selección son reproducibles por semilla. El plan selecciona familias completas sin repetición, aproxima la cuota por ejemplos y registra el resultado observado. Conserva los splits de evaluación y prueba de ambos releases. Usa estadísticas de tokens por track al diseñar experimentos para evitar que el mismo número de ejemplos implique presupuestos muy distintos.

```bash
rsec data replay-plan --cyber data/processed/reviewed-cyber/sft \
  --software data/processed/reviewed-software/sft \
  --max-rows 100 --software-share 0.5 --seed 42 --output reports/replay-plan.json

rsec data replay-plan --cyber data/processed/reviewed-cyber/sft \
  --software data/processed/reviewed-software/sft \
  --max-rows 100 --software-share 0.5 --seed 42 \
  --materialize --output data/processed/mixed-pilot
rsec data validate data/processed/mixed-pilot
```

Los comandos requieren releases aprobados. El release v3 contiene un plan verificable y snapshots locales v2. El entrenador existente puede consumirlo cuando su configuración indique ese `dataset` y se cumplan los gates de Fase 03. Mientras tanto se puede recorrer el mismo camino con los fixtures de pruebas.

## Medición de retención

Compara el modelo base, un adaptador especializado de control y un adaptador mixto con el mismo presupuesto de tokens de entrenamiento, semilla y configuración de inferencia. Registra diferencias por dominio, idioma y familia. Usa validación para elegir la mezcla y reserva las pruebas privadas para la decisión final. La cuota 50/50 es un punto de partida experimental. Una caída material en programación bloquea la promoción hasta revisar métricas y datos. Define tolerancias antes de medir.

CodeBench observa corrección funcional, pass@k, calidad, seguridad y resolución de problemas. CyberBench observa conclusiones sustentadas, errores de clasificación, CWE y acciones defensivas. Evalúa ambas suites antes y después de adaptar, fusionar o cuantizar. El [contrato de evaluación](../BENCHMARK_VALIDATION_REPORT.md) explica cómo mantener las condiciones comparables.

La profundidad por lenguaje, sistemas frontend/backend completos, tareas de repositorio, pruebas aisladas reproducibles y especialización avanzada se incorporan en las fases siguientes. La curación defensiva, la revisión humana y la validación física GPU siguen siendo el camino crítico de la fase actual.
