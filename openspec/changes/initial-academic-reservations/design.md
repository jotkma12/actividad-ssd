# Design

## Context

El repositorio no contiene código funcional ni especificaciones previas. `PLAN_INGENIERIA.md` establece una aplicación modular única con FastAPI, React y SQLite; fechas almacenadas en UTC y evaluadas en `America/Bogota`; bloques de 30 minutos; y validación/registro de reservas dentro de una transacción que adquiera el bloqueo de escritura, por ejemplo `BEGIN IMMEDIATE`. Los requisitos de comportamiento están en ocho archivos bajo `specs/`.

## Goals / Non-Goals

**Goals:**

- Mantener una única fuente de reglas para políticas, autorización y disponibilidad.
- Asegurar que creación y modificación de reservas no puedan confirmar horarios incompatibles ante solicitudes simultáneas.
- Conservar la relación entre cuentas, acciones y registros históricos aun después de desactivaciones y cambios de estado.
- Ordenar la futura implementación de acuerdo con las dependencias del plan.

**Non-Goals:**

- Definir endpoints, pantallas, tablas físicas, librerías adicionales o código de implementación.
- Incorporar registro público, avisos automáticos por correo, reportes, reservas separadas de equipos o integraciones universitarias.
- Incorporar el rol directivo/auditor en esta versión inicial; el plan condiciona los reportes al tiempo disponible y la propuesta inicial define tres roles.

## Decisions

### Límites modulares

Los módulos futuros corresponderán a las ocho capacidades de OpenSpec. `policies` será responsable de límites horarios, anticipación, duración y configuración de aprobación; `availability` determinará ocupación y cruces; `reservations` controlará estados y operaciones de reserva; `approvals` gestionará la revisión y decisión de solicitudes; `permissions` resolverá autorización; `history` conservará eventos. `spaces` administrará espacios y mantenimientos. Esta separación evita que cada operación repita reglas con posibles diferencias.

### Validación transaccional de horarios

La creación y modificación validarán disponibilidad y persistirán el resultado dentro de una sola transacción SQLite con bloqueo de escritura previo a la lectura, según el plan. Dos intervalos se cruzan exactamente cuando el inicio de A es anterior al fin de B y el inicio de B es anterior al fin de A. El inicio se incluye y el fin se excluye, por lo que una reserva puede comenzar cuando termina otra. Las reservas pendientes y aprobadas, junto con los bloqueos de mantenimiento, ocupan el horario.

Una espera agotada por contención debe producir un resultado claro y no guardar una reserva cuya disponibilidad no haya quedado comprobada. La alternativa de comprobar desde React o consultar y guardar en transacciones separadas no ofrece protección suficiente frente a solicitudes concurrentes.

### Fechas y horario

La interfaz y las reglas de negocio expresarán los horarios en `America/Bogota`; el almacenamiento seguirá la normalización UTC del plan. Los límites del calendario se aplicarán a la fecha local de inicio y fin y a la anticipación calculada desde el momento de la solicitud.

Las reglas temporales confirmadas para esta versión son: solicitar con al menos 24 horas y hasta 30 días de anticipación; permitir reservas de lunes a sábado entre las 07:00 y las 21:00; y permitir que el solicitante cancele una reserva aprobada hasta dos horas antes de su inicio. No habrá un límite máximo independiente de duración; toda reserva deberá respetar el horario permitido y las demás políticas.

### Cuentas y permisos

La configuración inicial del sistema permitirá crear un único primer administrador activo con nombre completo, correo terminado en `@universidad.edu.co` y contraseña válida. Solo estará disponible si todavía no existe un administrador; si ya existe uno, la configuración rechazará el intento y no creará otra cuenta inicial. El sistema no aprovisionará administradores iniciales automáticamente.

Las demás cuentas se crearán administrativamente, solo aceptarán correos terminados en `@universidad.edu.co` y comenzarán inactivas. Solo un administrador podrá activarlas. Todas las contraseñas, incluida la del administrador inicial, tendrán al menos 12 caracteres, sin requisitos de combinación de mayúsculas, minúsculas, números o símbolos. La desactivación no cancela reservas futuras: estas se conservan para que el administrador decida si las mantiene o las cancela; una cancelación administrativa debe registrar el motivo. Cada cuenta tendrá un rol principal. Los permisos se validarán en el servidor en cada operación protegida; ocultar una acción en React no sustituye esta validación. Los aprobadores se limitarán a espacios asignados y no podrán decidir sus propias solicitudes.

### Historial

Las operaciones que cambian entidades generarán eventos vinculados a actor, entidad y momento. Las cuentas y reservas se desactivarán o cambiarán de estado en vez de borrarse, para conservar las relaciones históricas. El acceso al historial seguirá el permiso de consulta de la entidad relacionada.

### Mantenimientos y comunicación con solicitantes

Solo un administrador podrá crear, modificar o retirar bloqueos de mantenimiento. Si el intervalo propuesto para crear o modificar un bloqueo se cruza con una reserva pendiente o aprobada, el sistema rechazará la operación e identificará las reservas afectadas; el bloqueo no se guardará mientras persista cualquiera de esos conflictos. El administrador deberá resolver primero esas reservas.

Cuando resolver un conflicto requiera cancelar o cambiar una reserva, el administrador será responsable de contactar manualmente a la persona solicitante. Podrá usar un canal institucional, por ejemplo una llamada o un mensaje. El sistema no enviará correos automáticos ni integrará servicios de notificación; no se fija un canal obligatorio.

### Alternativas descartadas

- **Microservicios:** el plan elige una aplicación modular por el alcance individual y la coordinación más sencilla.
- **PostgreSQL u hojas de cálculo:** SQLite es la base seleccionada para esta primera versión académica; las hojas no permiten controlar cruces con fiabilidad. Si el uso deja de ser moderado, el plan indica evaluar una migración futura.
- **Validación solo en cliente o fuera de transacción:** no evita que solicitudes casi simultáneas creen conflictos.
- **Borrado físico de reservas o usuarios:** impediría conservar el historial solicitado.

### Orden y dependencias de implementación

La base y la identidad preceden a la administración de espacios. El modelo y los estados de reserva se preparan antes del cálculo de disponibilidad, que necesita leer reservas, espacios y mantenimientos. La creación de solicitudes solo se habilita después de integrar esa validación en la misma transacción que guarda la reserva. Aprobaciones dependen de reservas y permisos; el historial se integra con las operaciones de cada módulo. La administración de mantenimientos aparece antes de disponibilidad porque esta debe considerarlos, aunque el plan ubica su cierre y validación final en la etapa final.
### Límites de los estados

`reservations` define los estados de una reserva y las transiciones de cancelación y finalización. `approvals` define la decisión que mueve una solicitud pendiente a aprobada o rechazada. `availability` interpreta qué estados ocupan un intervalo; no decide estados ni autorizaciones.

## Risks / Trade-offs

- [SQLite serializa las escrituras y tiene límites de concurrencia] → Mantener la transacción corta; configurar espera o devolver un mensaje claro; evaluar PostgreSQL solo si el crecimiento lo exige.
- [Reglas de calendario pueden interpretarse con otra zona horaria] → Evaluar y mostrar días/horas en `America/Bogota`, normalizando los instantes almacenados a UTC.
- [Una cuenta desactivada puede tener reservas futuras] → Decisión confirmada: conservarlas para revisión del administrador, sin cancelación automática.
- [Un cambio de una reserva aprobada puede dejar ocupaciones ambiguas mientras espera nueva aprobación] → No programar el flujo hasta resolver la pregunta de la siguiente sección.
- [El plan excluye avisos automáticos por correo] → Decisión confirmada: el administrador contacta manualmente a los solicitantes afectados por bloqueos de mantenimiento; no se integran servicios de notificación ni se fija un canal obligatorio.
- [Un bloqueo de mantenimiento podría coincidir con reservas existentes] → Decisión confirmada: rechazar la creación o modificación hasta resolver todas las reservas pendientes o aprobadas que se crucen con el intervalo.

## Migration Plan

No hay una aplicación ni datos funcionales que migrar en esta etapa. Durante una implementación futura, los cambios estructurales de SQLite deberán versionarse como indica el plan. Para desplegar o revertir esa implementación habrá que respaldar la base de datos y definir una restauración compatible; esa operación no forma parte de este cambio de especificaciones.

## Open Questions

- Cuando una solicitud pendiente llega a su hora de inicio o de fin sin decisión, ¿se cancela, se rechaza o permanece pendiente? El plan define el bloqueo temporal, pero no el vencimiento de una solicitud sin resolver.
- Cuando se modifica una reserva aprobada en un espacio que requiere aprobación, ¿la reserva original continúa ocupando su horario mientras se decide el cambio, o se libera al enviar la modificación? ¿Qué intervalo ocupa la modificación y qué ocurre con la reserva si se rechaza el cambio?
- Cuando se desactiva un espacio con reservas futuras, ¿qué canal manual y qué responsable se usarán para notificar a los solicitantes? El plan excluye avisos automáticos por correo y no define un canal alternativo.
- ¿Qué permisos de consulta tendrán los directivos/auditores si se habilitan reportes en una versión posterior? Se dejan fuera de los roles iniciales porque los reportes son opcionales y no forman parte de esta propuesta.
