# Validación de CyberBench y CodeBench

CyberBench conserva 32 casos públicos, 15 familias y 96 preauditorías al contar también los candidatos SFT. Sus etiquetas permiten comprobar el flujo de métricas deterministas. CodeBench incorpora 12 casos de desarrollo en 6 familias, con 6 preguntas EN y 6 ES. Ocho casos incluyen identificadores de comprobaciones funcionales y cuatro piden razonamiento de arquitectura o migraciones. Las suites tratan familias diferentes y ambas se reservan en la curación. No se midió desempeño de un modelo en esta fase.

```bash
rsec benchmark validate
rsec benchmark code-validate
rsec benchmark contamination-check --input data/pilot/candidates.jsonl
```

## Contrato de evidencia

El formato JSONL de predicciones se define en `rsec.datasets.evidence.Prediction`. Cada fila incluye ID y hash del caso, modelo/revisión, hashes de adaptador y artefacto, ordinal de muestra, condiciones de inferencia, base/revisión, tokenizer, plantilla, suite, system prompt, semilla, respuesta exacta y su hash. Para CodeBench el hash de caso resulta de `digest(CodeCase.model_validate(raw).model_dump())`. Para CyberBench usa `content_hash(Candidate.model_validate(raw))`. El hash de suite es SHA-256 de bytes. El hash de respuesta es `rsec.utils.digest(response)` sobre la cadena JSON. `Prediction.fingerprint()` une todo el registro.

Las evaluaciones exigen condiciones coincidentes, detectan muestras duplicadas y rechazan cambio de respuesta o rúbrica. `Rating` vincula fingerprint de predicción, hash de rúbrica, método, evaluador, fecha, evidencia, estado y puntuaciones. Se informan por separado métodos humano, IA asistida y adjudicación. Los resultados de la IA asistida se quedan en borrador. La agregación acepta evidencia local proporcionada por el operador. No certifica la identidad del evaluador ni autentica un harness externo.

```bash
rsec benchmark response-rubric --predictions reports/cyber-base.jsonl reports/cyber-mixed.jsonl \
  --ratings reports/cyber-ratings.jsonl --output reports/cyber-comparison.json

rsec benchmark code-evaluate --predictions reports/code-base.jsonl reports/code-mixed.jsonl \
  --unit-results reports/code-unit-evidence.jsonl --harness-sha256 SHA_REAL_DEL_HARNESS \
  --ratings reports/code-ratings.jsonl --k 1 5 --output reports/code-comparison.json
```

Estos comandos requieren artefactos de evaluación reales. Las comprobaciones de CodeBench tienen que registrar booleanos para todos los IDs de una muestra funcional. La cobertura debe ser completa y el presupuesto de muestras coincidir entre modelos. Una muestra es funcionalmente correcta cuando todas sus aserciones pasan. Para cada caso se calcula `1 − C(n − c, k) / C(n, k)`, se promedian casos y se devuelve null si faltan muestras para k. Los pesos de la rúbrica CodeBench v1 son 3 para resolución de problemas, 3 para corrección, 2 para mantenibilidad y 2 para seguridad. La rúbrica y las pruebas unitarias miden dimensiones distintas. La referencia del estimador está en [HumanEval](https://github.com/openai/human-eval/blob/master/human_eval/evaluation.py).

Conserva la salida exacta del modelo y los hashes antes de convertirla a un formato utilizable por la suite. `rsec predict` anterior sigue produciendo resultados para el scorer legacy de CyberBench. El formato rico de evidencia se importa explícitamente. Su producción automática por el runtime y el arnés aislado quedan para la siguiente fase. Las pruebas de contrato usaron resultados temporales conocidos, sin ejecutar las respuestas.

## Gold privado

El importador recibe casos Candidate v2, un mapa ID de caso a ID de autor, firmas de adjudicadores y catálogos locales. Verifica autor y adjudicador distintos, autoridad registrada, permisos, derechos y exclusión de familias relacionadas. El operador verifica la independencia de autoría y protege el mapa de autores. La suite se congela en `benchmarks/private/`, con contenido, firmas e inventario hash. El archivo se conserva fuera de Git y del proceso de selección de hiperparámetros. El test usó una identidad temporal y ninguna aprobación real.

```bash
rsec benchmark gold-import --cases benchmarks/private/inbox/cases.jsonl \
  --authors benchmarks/private/inbox/authors.json --reviews benchmarks/private/inbox/adjudications.jsonl \
  --reviewers data/reviews/reviewers.json --registry benchmarks/private/inbox/sources.json \
  --training data/processed/approved/sft/curation_records.jsonl --output benchmarks/private/final-v1
```

Para remediación y código generado comienza con revisión estática y sintáctica. Para pruebas dinámicas usa un arnés controlado en un entorno aislado sin red, secretos ni archivos del propietario, con filesystem efímero, privilegios mínimos y límites de CPU, RAM y tiempo. La instrumentación de resultados queda a cargo del arnés. El scorer trabaja sobre JSON y jamás ejecuta texto generado. Gold real, pruebas funcionales ejecutadas sobre salidas de modelos y comparación base/adaptador siguen pendientes.
