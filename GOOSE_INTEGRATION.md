# Inkling 2 Mini · Fase 03-B

El perfil alternativo usa el alias `inkling-2-mini` en la API OpenAI-compatible de un `llama-server` local. Arranca desde la revisión GGUF fijada y el build de llama.cpp indicado en [compatibilidad](INKLING_COMPATIBILITY.md), con `RSEC_LLAMA_PROFILE=inference-dual`, dos UUID explícitos y endpoint loopback. El modelo de 16,61 GB requiere ambas tarjetas para la ruta de offload descrita. El perfil gaming anterior conserva el modelo pequeño en la RTX 3060.

Selecciona `GOOSE_PATH_ROOT` nuevo, `GOOSE_PROVIDER=openai`, `GOOSE_MODEL=inkling-2-mini` y `OPENAI_HOST` con el loopback y puerto del servidor. Usa un valor local para la clave si el cliente exige uno. Las pruebas usan un repositorio temporal, un perfil separado y herramientas de fixture con una edición de aritmética predefinida. Se requiere observar una prueba roja, la corrección y una prueba verde, además de una respuesta estructurada. Los textos del modelo se tratan como datos. La configuración normal de Goose queda disponible en su perfil.

Con el servidor ya disponible, usa el lanzador existente para una sesión de chat con el perfil independiente `inkling`.

```powershell
& .\scripts\workstation.ps1 goose -GooseExe $GooseExe -GooseBackend openai `
  -GooseProfile inkling -Model inkling-2-mini -Port $InklingPort
```

La primera corrida física confirmó la sesión de Goose 1.54 con el proveedor OpenAI-compatible y las dos GPU mediante llama.cpp en WSL2. Con un tope de 256 tokens de salida, Goose terminó por longitud antes de llamar una herramienta. La sesión de texto y el flujo de desarrollo tienen resultados independientes.

**Flujo de desarrollo TESTED** con el servidor dual-GPU y el perfil temporal. En la segunda corrida se permitieron 1 024 tokens de salida por turno. Goose listó archivos, leyó el README, el código y la prueba, explicó la corrección, reprodujo el fallo, aplicó la edición permitida y verificó que la prueba pasaba. El informe final incluyó `tests_passed: true` en un objeto JSON. La extensión MCP limitó las operaciones al repositorio sintético y ejecutó una prueba fija revisada. La verificación directa del endpoint también pasó visión, esquema y nombre y argumentos de función. Este caso mide el flujo acotado de la fixture. [Mediciones](MULTI_GPU_VALIDATION.md)

---

# Goose · integración local

## RTX 3060 · v0.3.0-alpha.2

**GOOSE GPU INTEGRATION PASS WITH CONDITIONS.** Goose CLI 1.54 en Windows respondió en el perfil aislado con el endpoint OpenAI-compatible de llama.cpp b11552 en WSL2. El proceso recibió sólo el UUID de la RTX 3060. CUDA0 cargó 1,842 MiB de buffers de modelo y registró 31/31 capas. El peso GGUF se reutilizó desde disco mediante el modo de lectura directa y el servidor arrancó con modo offline.

Goose completó un turno de chat sin extensiones. En solicitudes separadas, el mismo endpoint devolvió una respuesta ajustada a JSON Schema y el nombre y argumentos de una llamada de herramienta benigna. La llamada se inspeccionó como datos. La integración del agente con herramientas de programación reales permanece pendiente. El perfil original de Goose permanece separado.

Para operar el perfil, inicia el [servidor WSL2](LOCAL_INFERENCE_GUIDE.md) en loopback y usa el lanzador Windows de Goose con el alias local-baseline y el mismo puerto. Las mediciones de latencia y generación están en el [benchmark](MULTI_GPU_BENCHMARK.md).

## Estación Windows · 2026-11-27

Goose CLI 1.54.0 y llama.cpp 0.6.0-dev están disponibles fuera de PATH. Se inspeccionaron los puertos habituales en la estación y se reutilizó el servidor instalado. Los detalles de enrutamiento de la configuración del propietario se guardan en un JSON privado mediante el lector selectivo `rsec.local goose-config`.

El lanzador usa un perfil aparte bajo `.rsec-local/goose` y un host de loopback. Comprueba el catálogo antes de iniciar Goose y desactiva las extensiones del perfil para esta sesión. La llave de ejemplo para el proveedor OpenAI-compatible identifica una conexión local con llama.cpp. Para el backend Ollama, usar la etiqueta exacta instalada y una instancia local en ejecución.

**TESTED.** Goose recibió el dígito solicitado desde el baseline GGUF local en llama.cpp, usando CPU con un hilo y cero capas en GPU. La configuración original se leyó de forma selectiva y el perfil de Rsec se ejecutó aparte.

```powershell
& .\scripts\workstation.ps1 inference -LlamaServerExe '<llama-server.exe>' -Model '<baseline.gguf>' -Threads 1 -DisableReasoning -Port 8081
# En otra consola, para comprobar únicamente la comunicación de chat:
& .\scripts\workstation.ps1 goose -GooseExe '<goose.exe>' -GooseBackend openai -Model local-baseline -Port 8081 -GooseSmoke
```

Tras verificar el chat, omitir `-GooseSmoke` para una sesión interactiva. `-DisableReasoning` asigna un presupuesto de razonamiento de cero tokens para este sondeo breve. El soporte de herramientas, la evaluación del modelo base y la sustitución por pesos futuros de Rsec requieren sus propias verificaciones.

[Documentación de proveedores Goose](https://goose-docs.ai/docs/getting-started/providers/) · [variables y perfil aislado](https://goose-docs.ai/docs/guides/environment-variables/)
