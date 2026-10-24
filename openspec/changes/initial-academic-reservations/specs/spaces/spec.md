# Spec Delta

## Purpose

Permite administrar los espacios académicos que pueden reservarse y registrar sus cierres por mantenimiento. Cada espacio conserva sus datos e historial cuando deja de aceptar nuevas reservas.

## ADDED Requirements

### Requirement: Registrar espacios académicos
El sistema SHALL permitir a un administrador registrar espacios con nombre, tipo, capacidad, ubicación, equipos disponibles y estado.

#### Scenario: Registrar un espacio válido
- **WHEN** un administrador registra un espacio con los datos requeridos
- **THEN** el sistema guarda el espacio y lo incluye en las consultas según su estado

#### Scenario: Datos requeridos ausentes o inválidos
- **WHEN** un administrador intenta registrar un espacio sin nombre, tipo, capacidad válida o ubicación
- **THEN** el sistema rechaza el registro e indica que los datos son inválidos

### Requirement: Consultar espacios
El sistema SHALL permitir consultar espacios y mostrar su tipo, capacidad, ubicación, equipos y estado.

#### Scenario: Consultar espacios registrados
- **WHEN** una persona consulta el listado de espacios
- **THEN** el sistema muestra los datos de cada espacio que esa persona tiene permiso para consultar

### Requirement: Editar espacios
El sistema SHALL permitir a un administrador actualizar los datos descriptivos de un espacio.

#### Scenario: Actualizar datos descriptivos
- **WHEN** un administrador guarda cambios válidos en un espacio existente
- **THEN** el sistema conserva los nuevos datos y registra el cambio en el historial

### Requirement: Desactivar espacios
El sistema SHALL permitir a un administrador desactivar un espacio para impedir nuevas reservas sin borrar sus datos ni sus reservas futuras.

#### Scenario: Desactivar espacio con reservas futuras
- **WHEN** un administrador desactiva un espacio que tiene reservas futuras
- **THEN** el espacio deja de aceptar nuevas reservas
- **AND** las reservas futuras existentes se conservan sin cancelarse automáticamente
- **AND** el sistema informa al administrador que debe revisar las reservas afectadas

#### Scenario: Consultar espacio desactivado
- **WHEN** una persona consulta un espacio desactivado
- **THEN** el sistema muestra que no acepta nuevas reservas y conserva su información histórica

### Requirement: Administrar bloqueos de mantenimiento
El sistema SHALL permitir únicamente a un administrador crear, modificar o retirar bloqueos asociados a un espacio, con inicio, fin y descripción del motivo.

#### Scenario: Crear bloqueo válido
- **WHEN** un administrador registra un bloqueo con inicio anterior al fin y una descripción
- **THEN** el sistema conserva el bloqueo asociado al espacio para las consultas y validaciones de disponibilidad

#### Scenario: Rechazar creación de bloqueo que coincide con una reserva pendiente
- **WHEN** un administrador intenta crear un bloqueo que se cruza con una reserva pendiente
- **THEN** el sistema rechaza la operación e identifica la reserva que debe resolverse
- **AND** no guarda el bloqueo

#### Scenario: Rechazar creación de bloqueo que coincide con una reserva aprobada
- **WHEN** un administrador intenta crear un bloqueo que se cruza con una reserva aprobada
- **THEN** el sistema rechaza la operación e identifica la reserva que debe resolverse
- **AND** no guarda el bloqueo

#### Scenario: Rechazar modificación de bloqueo con conflictos
- **WHEN** un administrador modifica un bloqueo y el nuevo intervalo se cruza con una reserva pendiente o aprobada
- **THEN** el sistema rechaza el cambio, conserva el bloqueo anterior e identifica las reservas que deben resolverse

#### Scenario: Guardar bloqueo después de resolver conflictos
- **WHEN** un administrador crea o modifica un bloqueo y ya no existen reservas pendientes o aprobadas que se crucen con el intervalo
- **THEN** el sistema guarda el bloqueo si sus demás datos son válidos

#### Scenario: Rechazar gestión de bloqueos sin permiso administrativo
- **WHEN** una persona que no es administradora intenta crear, modificar o retirar un bloqueo de mantenimiento
- **THEN** el sistema rechaza la operación y conserva el bloqueo sin cambios

#### Scenario: Contactar manualmente a solicitantes afectados
- **WHEN** resolver un conflicto con un bloqueo requiere cancelar o cambiar una reserva
- **THEN** el administrador es responsable de contactar manualmente al solicitante por un canal institucional, como una llamada o un mensaje
- **AND** el sistema no envía correos automáticos ni integra servicios de notificación

#### Scenario: Rechazar bloqueo inválido
- **WHEN** un administrador intenta guardar un bloqueo sin motivo o cuyo inicio no precede al fin
- **THEN** el sistema rechaza el bloqueo e indica los datos que deben corregirse

#### Scenario: Modificar o retirar bloqueo
- **WHEN** un administrador modifica o elimina un bloqueo existente
- **THEN** el sistema actualiza o retira ese bloqueo de la disponibilidad futura y registra la acción en el historial
