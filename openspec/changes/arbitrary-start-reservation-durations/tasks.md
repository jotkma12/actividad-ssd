# Tasks

## 1. Política de horarios del backend

- [x] 1.1 Cambiar la validación para aceptar inicio a cualquier minuto con precisión de minuto, manteniendo duraciones múltiplos de 30 y el límite consecutivo; añadir pruebas para inicio 10:17, duración de 30, rechazo de 45 minutos, máximo individual de cuatro horas y reglas de horario y anticipación.
- [x] 1.2 Añadir o actualizar pruebas API para creación, modificación y aprobación de intervalos con inicio arbitrario; verificar que los errores conserven la reserva original y que el límite acumulado existente siga aplicándose.

## 2. Selección de disponibilidad y reserva

- [x] 2.1 Cambiar disponibilidad a selección de inicio y duración entre 30 y 240 minutos en incrementos de 30; derivar el fin y usar exactamente el mismo intervalo en consulta y solicitud.
- [x] 2.2 Actualizar los recorridos Playwright para verificar 10:17 + 30 minutos = 10:47, opciones hasta cuatro horas, rechazo de intervalos inválidos por el servicio, conflictos y mensajes de error; actualizar documentación de uso.

## 3. Integración

- [x] 3.1 Ejecutar la suite pytest, build React, Playwright completo y validación OpenSpec estricta; revisar el límite de cuatro horas, conexión SQLite y que `PLAN_INGENIERIA.md` permanezca sin cambios.
