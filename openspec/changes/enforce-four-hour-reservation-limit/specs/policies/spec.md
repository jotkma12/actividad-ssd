# Spec Delta

## Purpose

Define el límite temporal acumulado que protege el acceso equitativo de los usuarios a cada espacio académico.

## ADDED Requirements

### Requirement: Limitar el tiempo consecutivo por usuario y espacio
El sistema SHALL limitar a cuatro horas el intervalo acumulado de reservas pendientes o aprobadas del mismo usuario en el mismo espacio cuando sus intervalos se tocan exactamente. Una pausa reinicia la secuencia y las reservas en espacios distintos se evalúan por separado.

#### Scenario: Aceptar exactamente cuatro horas consecutivas
- **WHEN** las reservas pendientes o aprobadas de un usuario forman una secuencia de exactamente cuatro horas en un espacio
- **THEN** el sistema acepta la operación si cumple las demás reglas

#### Scenario: Rechazar una reserva individual superior a cuatro horas
- **WHEN** un usuario solicita una reserva individual de cuatro horas y treinta minutos
- **THEN** el sistema rechaza la operación por superar el límite

#### Scenario: Acumular reservas consecutivas pendientes y aprobadas
- **WHEN** las reservas pendientes y aprobadas de un usuario en el mismo espacio se tocan exactamente y una nueva operación extiende la secuencia a más de cuatro horas
- **THEN** el sistema rechaza la operación

#### Scenario: Reiniciar el cómputo después de una pausa
- **WHEN** hay una pausa entre las reservas del usuario en el mismo espacio
- **THEN** el sistema calcula cada secuencia continua por separado

#### Scenario: No acumular reservas de espacios diferentes
- **WHEN** una reserva del usuario en otro espacio se toca en el tiempo con sus reservas de un espacio
- **THEN** el sistema evalúa cada espacio por separado

#### Scenario: Conservar reservas existentes que exceden el límite
- **WHEN** se activa la regla y una reserva ya existente supera cuatro horas consecutivas
- **THEN** el sistema conserva esa reserva vigente sin cancelarla ni modificarla automáticamente
