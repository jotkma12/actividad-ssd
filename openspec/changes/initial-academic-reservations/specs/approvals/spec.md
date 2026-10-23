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
