# Spec Delta

## Purpose

Define cómo las operaciones de reservas aplican las políticas temporales antes de guardar intervalos nuevos o modificados.

## ADDED Requirements

### Requirement: Aplicar el límite consecutivo al crear o modificar reservas
El sistema SHALL comprobar el límite de tiempo consecutivo del usuario y espacio al crear o modificar una reserva, considerando el intervalo solicitado como el intervalo que ocupará la reserva después de la operación.

#### Scenario: Rechazar una creación que supera el límite acumulado
- **WHEN** una nueva reserva se toca con otras reservas pendientes o aprobadas del mismo usuario y espacio y la secuencia resultante supera cuatro horas
- **THEN** el sistema rechaza la creación y no guarda una reserva nueva

#### Scenario: Rechazar una modificación que supera el límite
- **WHEN** el nuevo intervalo de una reserva modificada crea una secuencia superior a cuatro horas para el mismo usuario y espacio
- **THEN** el sistema rechaza la modificación y conserva el intervalo original

#### Scenario: Evaluar una modificación como reemplazo
- **WHEN** el sistema comprueba el límite para una modificación
- **THEN** evalúa el intervalo nuevo en lugar del intervalo actual de esa misma reserva y no suma ambos

#### Scenario: Rechazar una modificación incompatible de una reserva existente que excede el límite
- **WHEN** se intenta modificar una reserva existente que supera cuatro horas consecutivas y el intervalo propuesto incumple el límite
- **THEN** el sistema rechaza la modificación y conserva la reserva original sin cambios

#### Scenario: Mantener una reserva preexistente sin modificaciones
- **WHEN** una reserva existente supera cuatro horas consecutivas y no se intenta modificarla
- **THEN** el sistema la mantiene vigente sin cancelarla ni alterarla automáticamente
