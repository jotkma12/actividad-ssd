# Proposal

## Why

La universidad necesita reemplazar las solicitudes por correo y hojas de cálculo por reglas uniformes para consultar espacios, reservarlos y conservar quién tomó cada decisión. Esta propuesta define el comportamiento inicial antes de programar, con controles verificables para permisos, disponibilidad y solicitudes simultáneas.

## What Changes

- Definir la administración de espacios académicos y los bloqueos por mantenimiento.
- Definir la creación administrativa de cuentas, su activación y desactivación, y la conservación de su historial.
- Definir los roles de administrador, solicitante y aprobador, con permisos limitados a los espacios asignados.
- Definir la creación, consulta, modificación y cancelación de reservas.
- Definir por separado la revisión, aprobación y rechazo de solicitudes.
- Definir la disponibilidad y el rechazo de cruces entre reservas activas y mantenimientos, incluso ante solicitudes simultáneas.
- Definir bloques de duración, horario y anticipación para las reservas, sin máximo independiente de duración.
- Definir el registro consultable de acciones y cambios importantes.
- No implementar código, notificaciones automáticas, reportes, reservas de equipos por separado ni integraciones con otros sistemas universitarios.

## Capabilities

### New Capabilities

- `spaces`: registrar, consultar, editar y desactivar espacios, además de administrar sus bloqueos de mantenimiento.
- `users`: crear cuentas sin registro público, administrar datos y estado de las cuentas.
- `permissions`: asignar roles y autorizar acciones según rol y asignación de espacios.
- `reservations`: crear, consultar, modificar y cancelar reservas, y conservar su ciclo de vida.
- `availability`: consultar ocupación y disponibilidad considerando reservas activas y mantenimientos.
- `policies`: aplicar límites de duración, anticipación, horario y configuración de aprobación por espacio.
- `approvals`: permitir que aprobadores autorizados revisen y decidan solicitudes pendientes.
- `history`: conservar y permitir consultar los eventos relevantes de usuarios, espacios, reservas y decisiones.

### Modified Capabilities

Ninguna. No hay especificaciones existentes.

## Impact

El cambio establece contratos de comportamiento para los futuros módulos de FastAPI y React y para los datos guardados en SQLite. No modifica código ni APIs existentes. El diseño debe respetar la aplicación modular única, la hora `America/Bogota`, el almacenamiento uniforme en UTC y la comprobación transaccional de disponibilidad descritos en `PLAN_INGENIERIA.md`.

Como valores iniciales sujetos a confirmación del responsable del producto, se proponen: 24 horas de anticipación mínima, 30 días de anticipación máxima, lunes a sábado de 7:00 a. m. a 9:00 p. m. y cancelación de reservas aprobadas hasta dos horas antes. No se establece un límite independiente de duración por reserva; se mantienen los bloques de 30 minutos y el horario diario permitido. El plan excluye avisos automáticos por correo; por ello, cualquier aviso a solicitantes por desactivación de un espacio queda fuera del sistema y su canal/procedimiento necesita confirmación.
