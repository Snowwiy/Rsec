# Goose · integración local

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
