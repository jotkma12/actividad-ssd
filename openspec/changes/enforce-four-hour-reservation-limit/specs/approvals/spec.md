# Spec Delta

## Purpose

Define la validación final de las modificaciones de horario que requieren la decisión de un aprobador autorizado.

## ADDED Requirements

### Requirement: Revalidar el límite consecutivo al aprobar un cambio de horario
El sistema SHALL aprobar un cambio de horario únicamente si el intervalo propuesto, considerado como alternativa al intervalo original, respeta el máximo de cuatro horas consecutivas para el usuario y espacio.

#### Scenario: No sumar la propuesta y el intervalo original mientras esperan decisión
- **WHEN** una reserva aprobada tiene una modificación de horario pendiente de aprobación
- **THEN** el sistema evalúa el intervalo propuesto como alternativa al original y no cuenta ambos simultáneamente para el límite

#### Scenario: Aprobar cambio que continúa dentro del límite
- **WHEN** el aprobador asignado decide un cambio y el intervalo propuesto como reemplazo mantiene la secuencia en cuatro horas o menos
- **THEN** el sistema aprueba el cambio y reemplaza el intervalo original

#### Scenario: Impedir cambio que supera el límite al aprobarse
- **WHEN** el aprobador asignado intenta aprobar un cambio cuyo intervalo propuesto como reemplazo supera cuatro horas consecutivas con otras reservas pendientes o aprobadas del mismo usuario y espacio
- **THEN** el sistema impide la aprobación y conserva aprobada la reserva con el intervalo original
- **AND** no sustituye el intervalo original por el propuesto
