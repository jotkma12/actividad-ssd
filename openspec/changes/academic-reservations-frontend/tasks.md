# Tasks

## 1. Autenticación y página principal

- [x] 1.1 Implementar el cliente HTTP configurable, el proxy de Vite, el inicio y cierre de sesión y la página principal según rol; añadir pruebas Playwright que inicien FastAPI con una SQLite desechable y documenten los comandos de ejecución. Verificar acceso correcto, cuenta inactiva, error de red, secciones por rol y cierre de sesión.

## 2. Gestión de espacios

- [x] 2.1 Implementar consulta y administración de espacios, configuración de aprobación y bloqueos de mantenimiento; añadir recorridos Playwright y documentar las operaciones. Verificar permisos, persistencia real, conflicto de mantenimiento y reservas futuras al desactivar.

## 3. Administración de usuarios

- [x] 3.1 Añadir el endpoint faltante para editar nombre, correo institucional e identificación con validación transaccional e historial; implementar la interfaz de cuentas, activación, roles y asignaciones. Verificar reglas de usuarios con pytest y recorridos Playwright contra FastAPI.

## 4. Disponibilidad

- [x] 4.1 Implementar la consulta tabular por fecha, hora y espacio mediante los endpoints reales; añadir pruebas Playwright para resultados disponibles, ocupados, bloqueados y errores. Verificar que la interfaz no marque resultados sin confirmación del servicio.

## 5. Reservas

- [x] 5.1 Implementar solicitud, consulta, modificación y cancelación de reservas propias; añadir recorridos Playwright y documentar los estados y respuestas. Verificar reglas temporales, duración acumulada de cuatro horas, disponibilidad, permisos, plazos y conservación de la reserva original ante errores.

## 6. Aprobaciones

- [x] 6.1 Implementar bandejas de solicitudes y cambios, aprobación y rechazo con motivo; añadir recorridos Playwright contra el backend real. Verificar asignación de espacios, rechazo sin motivo, vencimiento, revalidación del límite de cuatro horas y conservación del intervalo original si una aprobación falla.

## 7. Historial

- [x] 7.1 Implementar filtros y vista de eventos permitidos según el rol; añadir recorridos Playwright y documentar la consulta. Verificar que cada rol solo vea eventos autorizados devueltos por el backend.

## 8. Integración final

- [x] 8.1 Ejecutar la suite pytest, el build de React y los recorridos Playwright completos; validar el cambio con OpenSpec estricto y revisar los cambios por módulo. Verificar conexión real con SQLite, que `PLAN_INGENIERIA.md` no cambie y que cada módulo pueda proponerse como commit separado.
