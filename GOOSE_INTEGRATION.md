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
