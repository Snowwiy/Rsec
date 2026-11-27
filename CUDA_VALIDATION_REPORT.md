# CUDA · validación pendiente de hardware

El diagnóstico independiente detectó cero dispositivos CUDA en el ejecutor. Quedan sin medir FP16, BF16 nativo, asignación/liberación, consumo y rendimiento de la 4070. En Windows se admiten CLI, revisión e inferencia según el binario instalado. Usar primero WSL2 para validar el stack Linux de entrenamiento.

La prueba supervisada consulta el sensor por UUID antes de lanzar el proceso. El hijo ve únicamente ese dispositivo; exige tensores CUDA y resultados correctos al multiplicar matrices FP16 y, cuando esté soportado, BF16. El informe de la prueba registra memoria máxima asignada por Torch y memoria libre después de liberar el modelo. Contrastar ambas con memoria de dispositivo reportada por NVIDIA. Sólo admitir una ejecución con informe final, identidad confirmada y supervisor completado. Conservar la salida de error si falla.
