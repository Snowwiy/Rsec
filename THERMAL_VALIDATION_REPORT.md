# Monitorización térmica · v0.3.0-alpha.2

**PASS WITH CONDITIONS.** Ambas GPU se observaron durante las cargas CUDA de la fase. Los máximos fueron 54.3 °C en la 4070 y 66.8 °C en la 3060. Se observaron cero avisos a 80 °C y cero muestras de limitación térmica activa. Las ventanas de cálculo fueron breves. La estabilidad sostenida con un videojuego simultáneo queda pendiente.

El supervisor CUDA toma una muestra por segundo más la latencia de NVIDIA. Registra núcleo, utilización, frecuencia SM, VRAM, potencia, límite efectivo, ventilador, PCIe y razones térmicas cuando están disponibles. El hotspot no aparece en los campos expuestos por el runtime. La prueba de inferencia registró la misma telemetría con un intervalo objetivo de medio segundo. Los picos breves entre muestras pueden quedar fuera del registro. [Mediciones por ejecución](MULTI_GPU_BENCHMARK.md)

Se advierte a 80 °C. A 85 °C, ante throttling térmico, pérdida de sensor, fallo de proceso o límite de tiempo se detiene el proceso propio. Los registros completos permanecen en almacenamiento privado. Las pruebas moderadas no modificaron límites, frecuencias ni ventiladores.
