# Identidad y firmas del revisor

La interfaz opera en IPv4 loopback. Valida Host, origen para POST, token CSRF y confirmación explícita; los campos del dataset se escapan antes de entrar en HTML. El modo con clave concede al proceso local autoridad para firmar actos individuales del revisor. Usa una cuenta local confiable y mantén el puerto en loopback. Cada evento firmado se guarda en un archivo nuevo. Una firma evidencia control de la clave registrada. La competencia, identidad humana y custodia de claves se verifican fuera de la aplicación.

Ejemplo para un operador real en Linux/WSL2, usando OpenSSL 3 y un directorio local con acceso limitado. Ejecuta la generación solo si aún no tienes una clave.

```bash
umask 077
mkdir -p data/reviews/private
openssl genpkey -algorithm Ed25519 -out data/reviews/private/reviewer.pem
openssl pkey -in data/reviews/private/reviewer.pem -pubout -out data/reviews/reviewer-public.pem
sha256sum data/reviews/reviewer-public.pem
```

Crea `data/reviews/reviewers.json` con esta estructura y valores elegidos por el propietario. Los marcadores de ejemplo requieren sustitución.

```json
{
  "reviewers": [{
    "id": "ID_REAL",
    "display_name": "NOMBRE_LOCAL",
    "domains": ["application_security", "software_engineering"],
    "active": true,
    "added_on": "2026-11-26",
    "public_key": "reviewer-public.pem",
    "key_sha256": "SHA256_REAL_DEL_PEM_PUBLICO",
    "permissions": ["review"],
    "fixture": false
  }]
}
```

Elige dominios según competencias reales. Concede `adjudicate` solo a quien evalúe gold de manera independiente. Distintos revisores necesitan claves distintas. Los eventos vinculan hash de contenido, revisión, catálogo, política, identidad, decisión, checks, comentarios, propuesta y fecha. La exportación valida nuevamente los eventos y bloquea registros con objeciones abiertas. El modo actual usa PEM Ed25519 local sin contraseña interactiva. Restringe permisos del archivo y cierra la UI cuando termine la sesión.

Guarda las autoridades y eventos fuera del Git público. Desactiva el registro de una clave comprometida, conserva el ledger y revalida decisiones a través de la nueva autoridad antes de usar un release. Los registros marcados `fixture` se rechazan. Las pruebas efectivas de firma usan una autoridad desechable en un workspace temporal y marcan las identidades como de prueba en los nombres. No hay identidades, claves o firmas reales de aprobación distribuidas con el proyecto.

El bridge v2 compatible sigue aceptando decisiones normalizadas. Esa interfaz no autentica un JSONL editado a mano. Para producción conserva el ledger firmado como evidencia y genera el JSONL a través de la exportación verificada antes de relanzar la curación.
