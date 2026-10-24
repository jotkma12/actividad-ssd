# Tasks

## 1. Base del proyecto

- [x] 1.1 Preparar la aplicación modular FastAPI/React y la configuración SQLite prevista en el plan; verificar que el proyecto inicia y crea la base sin errores.
- [x] 1.2 Preparar cambios versionados de base de datos para usuarios, espacios, reservas, mantenimientos e historial; verificar creación y actualización desde una base vacía.

## 2. Usuarios y permisos (depende de la base del proyecto)

- [x] 2.1 Confirmar dominio institucional, estado inicial de cuentas nuevas y tratamiento de reservas futuras al desactivar cuentas; verificar que las decisiones estén aprobadas y reflejadas en los escenarios.
- [x] 2.2 Implementar autenticación, configuración inicial de un único primer administrador activo y creación administrativa de cuentas inactivas; verificar dominio institucional, contraseña mínima de 12 caracteres, datos válidos, duplicados, datos ausentes, rechazo del registro público y prevención de un segundo administrador inicial.
- [x] 2.3 Implementar activación y desactivación de cuentas conforme a las decisiones confirmadas; verificar acceso denegado a cuentas inactivas y conservación del historial.
- [x] 2.4 Implementar roles principales, matriz de permisos y asignaciones de aprobadores por espacio; verificar acciones permitidas y denegadas para los tres roles.
- [x] 2.5 Agregar pruebas unitarias y documentación de cuentas y permisos; verificar cobertura de sesión, estado de cuenta, propiedad de reservas y asignación de espacios.

## 3. Espacios y mantenimiento (depende de usuarios y permisos)

- [x] 3.1 Implementar alta, consulta, edición y desactivación de espacios; verificar datos requeridos, conservación histórica y rechazo de nuevas reservas en espacios inactivos.
- [x] 3.2 Implementar gestión de bloqueos de mantenimiento; restringirla a administradores, rechazar altas o modificaciones que se crucen con reservas pendientes o aprobadas, y dejar el contacto a solicitantes afectados como responsabilidad manual del administrador sin notificaciones automáticas.
- [x] 3.3 Agregar pruebas de integración y documentación de espacios y mantenimientos; verificar que se revisen las reservas futuras al desactivar un espacio.

## 4. Políticas (depende de espacios)

- [x] 4.1 Confirmar anticipación mínima y máxima, horario semanal y plazo de cancelación; verificar que las decisiones estén aprobadas y reflejadas en los requisitos, sin añadir un máximo de duración.
- [x] 4.2 Implementar bloques de 30 minutos, horario y anticipación en `America/Bogota`; verificar una reserva de más de cuatro horas dentro de la jornada y casos fuera de horario.
- [x] 4.3 Implementar configuración de aprobación por espacio; verificar que la regla sea obligatoria y que cambios afecten nuevas solicitudes sin cambiar reservas existentes.
- [x] 4.4 Agregar pruebas unitarias y documentación de políticas; verificar valores aprobados y que no exista máximo independiente de duración.

## 5. Modelo de reservas (depende de usuarios, permisos, espacios y políticas)

- [x] 5.1 Implementar persistencia y consulta de reservas con los estados pendiente, aprobada, rechazada, cancelada y finalizada; verificar estado inicial según la política y conservación de estados terminales.
- [x] 5.2 Implementar cancelaciones por solicitante y administrador con los plazos y motivos definidos; verificar casos permitidos, denegados y conservación del registro.
- [x] 5.3 Agregar pruebas unitarias y documentación del ciclo de reserva; verificar transiciones de cancelación y finalización.

## 6. Disponibilidad (depende del modelo de reservas, espacios y mantenimientos)

- [x] 6.1 Implementar consulta de disponibilidad usando reservas pendientes/aprobadas, espacios activos y mantenimientos; verificar intervalos parcialmente coincidentes y consecutivos.
- [x] 6.2 Implementar validación de coincidencias para creación/cambio de mantenimientos; verificar la regla de negocio confirmada y el tratamiento de reservas afectadas.
- [x] 6.3 Agregar pruebas de integración y documentación de disponibilidad; verificar que reservas rechazadas, canceladas y finalizadas liberen el horario.

## 7. Solicitudes de reserva (depende de disponibilidad y políticas)

- [ ] 7.1 Implementar creación de reservas para solicitantes activos y espacios activos; verificar rechazo de reglas incumplidas y estado inicial según aprobación configurada.
- [ ] 7.2 Hacer atómica la comprobación y escritura de reservas mediante la transacción SQLite prevista; verificar con 20 solicitudes simultáneas incompatibles que como máximo una quede aceptada.
- [ ] 7.3 Implementar consulta y modificación de reservas pendientes/aprobadas; verificar propiedad, plazos, políticas y disponibilidad del nuevo intervalo.
- [ ] 7.4 Agregar pruebas de integración y concurrencia; verificar que errores de disponibilidad o contención no dejen registros incompatibles.

## 8. Aprobaciones (depende de reservas y permisos)

- [ ] 8.1 Implementar bandeja de solicitudes pendientes limitada a espacios asignados; verificar que no se revelen solicitudes de otros espacios.
- [ ] 8.2 Confirmar qué ocurre cuando una solicitud pendiente llega a su inicio o fin sin decisión; actualizar los escenarios y verificar que la regla quede aprobada antes de implementar vencimientos.
- [ ] 8.3 Implementar aprobación y rechazo con motivo obligatorio; verificar cambios de estado, rechazo sin motivo, decisiones repetidas y decisiones concurrentes.
- [ ] 8.4 Acordar qué intervalo bloquea una modificación que requiere nueva aprobación y qué ocurre si se rechaza; actualizar escenarios antes de implementar ese flujo.
- [ ] 8.5 Agregar pruebas de integración y documentación de aprobaciones; verificar asignación, prohibición de autoaprobación y estados válidos.

## 9. Historial (depende de usuarios y de las operaciones de cada módulo)

- [ ] 9.1 Registrar actor, momento, acción y cambios para cuentas, roles, espacios, mantenimientos, reservas y decisiones; verificar eventos para operaciones correctas.
- [ ] 9.2 Implementar consulta según permisos e impedir edición/borrado normal de eventos; verificar acceso del administrador, solicitante y aprobador según su alcance.
- [ ] 9.3 Agregar pruebas de integración y documentación de historial; verificar motivos, orden cronológico y conservación tras desactivar cuentas.

## 10. Integración

- [ ] 10.1 Ejecutar recorridos completos de cuenta, espacio, solicitud, disponibilidad, aprobación/rechazo, cancelación e historial; verificar los escenarios acordados.
- [ ] 10.2 Actualizar trazabilidad requisito-prueba y revisar documentación del sistema; verificar que ningún requisito implementado quede sin prueba asociada.
