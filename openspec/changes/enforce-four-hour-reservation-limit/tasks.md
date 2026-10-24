# Tasks

## 1. Decisión previa para datos existentes

- [x] 1.1 Documentar que las reservas existentes que superen cuatro horas consecutivas se conservan sin cambios, que una modificación incompatible se rechaza y que no se realizan ajustes automáticos; verificar escenarios y coherencia con el diseño.

## 2. Política de duración

- [x] 2.1 Implementar el cálculo de secuencias para el mismo usuario y espacio, aceptando cuatro horas exactas y separando secuencias con pausas o espacios diferentes; verificar con pruebas unitarias reservas individuales, combinación de estados pendiente/aprobada y los límites de duración.
- [x] 2.2 Sustituir en pruebas y documentación los ejemplos que permiten duraciones mayores a cuatro horas; verificar que la guía y la matriz de trazabilidad describan la regla acumulada confirmada.

## 3. Creación y modificación de reservas

- [x] 3.1 Integrar la comprobación de duración en la transacción SQLite de creación y modificación, excluyendo el intervalo actual cuando se evalúa su reemplazo; verificar rechazos sin escrituras, pausas, espacios distintos y operaciones concurrentes.

## 4. Cambios aprobados

- [x] 4.1 Comprobar el intervalo propuesto como alternativa al original al solicitar un cambio y volver a comprobarlo al aprobar; verificar que un exceso impida la aprobación y conserve la reserva original aprobada.

## 5. Verificación integrada

- [x] 5.1 Ejecutar los recorridos integrados y la suite completa, comprobar los escenarios positivos y negativos y validar el cambio con OpenSpec en modo estricto; verificar que no se altere `PLAN_INGENIERIA.md`.
