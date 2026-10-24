# Spec Delta

## Purpose

Permite revisar solicitudes de reserva pendientes y registrar una decisión autorizada. Las decisiones siguen las asignaciones por espacio y el ciclo de estados definido para las reservas.

## ADDED Requirements

### Requirement: Consultar solicitudes pendientes asignadas
El sistema SHALL mostrar a cada aprobador las solicitudes pendientes de los espacios que tiene asignados.

#### Scenario: Aprobador consulta pendientes de sus espacios
- **WHEN** un aprobador consulta su bandeja de solicitudes
- **THEN** el sistema muestra las solicitudes pendientes de sus espacios asignados

#### Scenario: Aprobador no ve pendientes de otros espacios
- **WHEN** existen solicitudes pendientes en espacios no asignados al aprobador
- **THEN** el sistema no las incluye en su bandeja ni revela sus detalles

### Requirement: Resolver una solicitud pendiente
El sistema SHALL permitir a un aprobador autorizado aprobar o rechazar una solicitud que todavía esté pendiente.

#### Scenario: Aprobación autorizada
- **WHEN** un aprobador asignado aprueba una solicitud pendiente que no creó él mismo
- **THEN** el sistema registra la decisión y cambia la reserva a aprobada

#### Scenario: Rechazo autorizado con motivo
- **WHEN** un aprobador asignado rechaza una solicitud pendiente e indica un motivo no vacío
- **THEN** el sistema registra la decisión y cambia la reserva a rechazada
- **AND** conserva el motivo asociado a la decisión

#### Scenario: Rechazo sin motivo
- **WHEN** un aprobador intenta rechazar una solicitud pendiente sin indicar un motivo
- **THEN** el sistema rechaza la decisión y mantiene la reserva pendiente

#### Scenario: Decisión sobre una solicitud ya resuelta
- **WHEN** un aprobador intenta decidir una solicitud que ya no está pendiente
- **THEN** el sistema rechaza la operación y conserva el estado actual

#### Scenario: Dos decisiones concurrentes
- **WHEN** dos aprobadores intentan resolver simultáneamente la misma solicitud pendiente
- **THEN** solo una decisión cambia el estado de la reserva
- **AND** la otra operación informa que la solicitud ya fue resuelta

### Requirement: Vencer solicitudes pendientes al inicio del horario
El sistema SHALL cambiar automáticamente a «Rechazada por vencimiento» una solicitud que continúe pendiente al llegar su hora de inicio, registrar el motivo del rechazo y liberar el horario solicitado.

#### Scenario: Solicitud pendiente alcanza su inicio
- **WHEN** llega la hora de inicio de una solicitud que aún está pendiente
- **THEN** el sistema la cambia a «Rechazada por vencimiento» y registra que venció sin decisión
- **AND** el horario deja de estar ocupado por esa solicitud, salvo que otra reserva o bloqueo lo ocupe

#### Scenario: Aprobador intenta aprobar una solicitud vencida
- **WHEN** un aprobador intenta aprobar una solicitud cuya hora de inicio ya llegó sin una decisión previa
- **THEN** el sistema rechaza la operación y conserva «Rechazada por vencimiento»

#### Scenario: Vencimiento compite con una decisión
- **WHEN** el vencimiento automático y una decisión autorizada intentan cambiar la misma solicitud pendiente
- **THEN** solo una transición se registra
- **AND** una solicitud vencida no puede terminar aprobada

### Requirement: Solicitar aprobación para cambiar una reserva aprobada
El sistema SHALL mantener aprobada y ocupando su intervalo original una reserva cuyo solicitante pida un cambio que requiere aprobación, y SHALL bloquear provisionalmente el nuevo intervalo si cumple las políticas y está disponible.

#### Scenario: Solicitar cambio con nuevo horario disponible
- **WHEN** el solicitante pide dentro del plazo permitido cambiar una reserva aprobada en un espacio que requiere aprobación y el nuevo horario cumple las políticas y está disponible
- **THEN** el sistema mantiene aprobada la reserva y ocupado su intervalo original
- **AND** bloquea provisionalmente el nuevo horario mientras espera una decisión

#### Scenario: Nuevo horario incumple reglas o tiene conflicto
- **WHEN** el solicitante pide un cambio cuyo nuevo horario incumple las restricciones temporales o se cruza con una reserva, otro cambio pendiente o un bloqueo de mantenimiento
- **THEN** el sistema rechaza la solicitud de cambio sin modificar la reserva aprobada ni bloquear el nuevo horario

#### Scenario: Aprobador autoriza el cambio
- **WHEN** un aprobador asignado aprueba el cambio pendiente
- **THEN** el sistema actualiza la reserva aprobada con el nuevo horario y libera el intervalo original
- **AND** conserva el nuevo horario como ocupado por la reserva aprobada

#### Scenario: Aprobador rechaza el cambio
- **WHEN** un aprobador asignado rechaza el cambio pendiente e indica un motivo no vacío
- **THEN** el sistema libera el bloqueo provisional del nuevo horario
- **AND** conserva la reserva original aprobada con sus fechas y horas originales

#### Scenario: Cambio pendiente no se decide más de una vez
- **WHEN** una persona intenta aprobar o rechazar un cambio que ya fue resuelto
- **THEN** el sistema rechaza la segunda decisión y conserva el resultado existente
