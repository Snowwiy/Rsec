# Revisión humana local · Fase 02-B

Desde la raíz, instala el paquete. Elige destinos nuevos para los bundles. La preauditoría incluida corresponde a los hashes congelados de los 96 registros originales. Puedes reproducirla sin PyTorch.

```bash
rsec data preaudit --input data/pilot/candidates.jsonl benchmarks/rsec_cyberbench/development.jsonl \
  --output reports/preaudit.jsonl
rsec data curate --input data/pilot/candidates.jsonl --version pilot-review-1 \
  --output data/processed/pilot-review-1
rsec data review data/processed/pilot-review-1 --output reports/review-packet.json
rsec data review-ui data/processed/pilot-review-1 --preaudit reports/preaudit.jsonl
```

Abre `http://127.0.0.1:8765`. Con esa invocación puedes leer contenido y fuentes. Para registrar decisiones habilita tu clave local según [REVIEWER_SECURITY.md](REVIEWER_SECURITY.md).

```bash
rsec data review-ui data/processed/pilot-review-1 --preaudit reports/preaudit.jsonl \
  --reviewers data/reviews/reviewers.json --reviewer ID_REAL \
  --private-key data/reviews/private/reviewer.pem --ledger data/reviews/pilot-events
```

En cada registro confirma el razonamiento, evidencia, referencias, licencia y privacidad. Revisa la remediación cuando aplique. Contrasta idioma y dificultad con el problema. Marca una decisión explícita por revisión. Para corregir, guarda una propuesta y compárala con el original. El operador crea un nuevo registro con nuevo ID/revisión y enlaces de familia, para que reciba su propia revisión. Las objeciones bloquean promoción de esa revisión.

```bash
rsec data review-export data/processed/pilot-review-1 \
  --reviewers data/reviews/reviewers.json --ledger data/reviews/pilot-events \
  --output data/reviews/pilot-decisions.jsonl
rsec data curate --input data/pilot/candidates.jsonl --decisions data/reviews/pilot-decisions.jsonl \
  --version pilot-reviewed-1 --output data/processed/pilot-reviewed-1
rsec data validate data/processed/pilot-reviewed-1
```

`review-export --import-events ARCHIVO` valida firmas y hashes de un JSONL autorizado y combina sus eventos con el ledger local para exportar. Conserva por separado los eventos firmados, el registro de revisores y el archivo de decisiones. El bridge existente recibe decisiones normalizadas. Se requiere un segundo revisor activo e independiente para dificultad avanzada o experta, y al menos tres familias aprobadas para crear train/eval/test. Reporta aprobación únicamente tras una decisión real.

Para revisar la suite pública de CyberBench crea otro bundle y reserva los casos de Fase 01 y CodeBench. La suite de entrada no debe reservarse contra sí misma.

```bash
rsec data curate --input benchmarks/rsec_cyberbench/development.jsonl \
  --reserved benchmarks/suite.jsonl benchmarks/rsec_codebench/development.jsonl \
  --version cyberbench-review-1 --output data/processed/cyberbench-review-1
```
