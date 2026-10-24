# Spec Delta

## Purpose

Permite consultar si un espacio está libre para un intervalo y proporciona una decisión consistente al crear o cambiar reservas. Considera tanto reservas activas como cierres de mantenimiento.

## ADDED Requirements

### Requirement: Consultar disponibilidad de un espacio
El sistema SHALL informar si un espacio está libre, ocupado o bloqueado para el intervalo consultado. También considerará ocupados los nuevos intervalos bloqueados provisionalmente por cambios de reservas aprobadas que esperan decisión.

#### Scenario: Intervalo sin ocupación ni mantenimiento
- **WHEN** una persona autorizada consulta un intervalo sin reserva activa ni bloqueo de mantenimiento
- **THEN** el sistema informa que el espacio está disponible

#### Scenario: Intervalo ocupado por reserva activa
- **WHEN** una persona consulta un intervalo que se cruza con una reserva pendiente o aprobada
- **THEN** el sistema informa que el espacio está ocupado

#### Scenario: Intervalo bloqueado por mantenimiento
- **WHEN** una persona consulta un intervalo que se cruza con un bloqueo de mantenimiento
- **THEN** el sistema informa que el espacio está bloqueado

#### Scenario: Intervalo bloqueado provisionalmente por un cambio pendiente
- **WHEN** una persona consulta un intervalo que se cruza con el nuevo horario de un cambio pendiente de aprobación
- **THEN** el sistema informa que el intervalo está ocupado

### Requirement: Determinar cruces de horario
El sistema SHALL considerar que dos intervalos A y B se cruzan exactamente cuando inicio A < fin B e inicio B < fin A.

#### Scenario: Intervalos parcialmente coincidentes
- **WHEN** el inicio de una reserva propuesta es anterior al fin de una reserva activa y el inicio de la reserva activa es anterior al fin de la propuesta
- **THEN** el sistema considera que los intervalos se cruzan y no permite ocupar ambos

#### Scenario: Intervalos consecutivos
- **WHEN** una reserva empieza exactamente cuando termina otra reserva o un bloqueo
- **THEN** el sistema no considera que los intervalos se cruzan

### Requirement: Validar y guardar sin carreras
El sistema SHALL comprobar la disponibilidad y guardar una reserva o modificación dentro de una misma operación atómica.

#### Scenario: Solicitudes simultáneas incompatibles
- **WHEN** varias solicitudes simultáneas intentan reservar el mismo espacio en intervalos que se cruzan
- **THEN** ante 20 solicitudes simultáneas que se cruzan para el mismo espacio, como máximo una queda guardada como pendiente o aprobada
- **AND** las demás se rechazan sin crear reservas incompatibles

#### Scenario: La base de datos está ocupada
- **WHEN** otra operación mantiene ocupado el acceso de escritura mientras se valida una reserva
- **THEN** el sistema espera o informa claramente que no pudo completar la operación
- **AND** no guarda una reserva sin haber confirmado su disponibilidad

### Requirement: Excluir estados que liberan el horario
El sistema SHALL tratar como ocupantes del horario las reservas pendientes y aprobadas y los nuevos intervalos bloqueados provisionalmente por cambios pendientes. Los rechazos ordinarios, rechazos por vencimiento, cancelaciones, finalizaciones y cambios rechazados no ocuparán el horario.

#### Scenario: Reserva rechazada, vencida, cancelada o finalizada
- **WHEN** se consulta un horario ocupado previamente solo por una reserva rechazada, rechazada por vencimiento, cancelada o finalizada
- **THEN** esa reserva no impide que el horario vuelva a estar disponible

#### Scenario: Cambio pendiente rechazado libera su nuevo intervalo
- **WHEN** se consulta el nuevo horario de un cambio que fue rechazado y no existe otra ocupación
- **THEN** el bloqueo provisional ya no impide reservarlo
