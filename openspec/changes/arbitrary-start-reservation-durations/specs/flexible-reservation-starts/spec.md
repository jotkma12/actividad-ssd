# Spec Delta

## Purpose

Permite elegir el inicio de una reserva con precisión de minuto y elegir su duración en tramos de 30 minutos, manteniendo los límites de horario, disponibilidad y tiempo consecutivo del sistema.

## ADDED Requirements

### Requirement: Elegir un inicio libre y una duración en tramos de treinta minutos
El sistema SHALL permitir que una reserva comience en cualquier minuto permitido y SHALL requerir una duración de al menos 30 minutos que sea múltiplo de 30 y no supere cuatro horas. El fin SHALL calcularse sumando la duración elegida al inicio. Esta regla reemplaza la exigencia de que el inicio y el fin coincidan con `:00` o `:30`; las demás políticas de reserva siguen vigentes.

#### Scenario: Crear reserva con inicio que no cae en :00 o :30
- **WHEN** un solicitante pide una reserva que inicia a las 10:17 y dura 30 minutos
- **THEN** el sistema valida el intervalo de 10:17 a 10:47 conforme a las demás políticas y disponibilidad

#### Scenario: Ofrecer duraciones en incrementos de 30 minutos
- **WHEN** un solicitante selecciona la duración de una reserva
- **THEN** puede elegir 30, 60, 90 y sucesivos múltiplos de 30 minutos hasta 240 minutos

#### Scenario: Rechazar duración que no sea múltiplo de treinta minutos
- **WHEN** una operación solicita una duración de 45 minutos
- **THEN** el sistema rechaza la reserva e informa que la duración debe ser múltiplo de 30 minutos

#### Scenario: Rechazar una duración superior a cuatro horas
- **WHEN** una operación solicita una duración mayor a 240 minutos
- **THEN** el sistema rechaza la reserva y conserva el límite acumulado consecutivo vigente

#### Scenario: Mantener políticas de horario y límite acumulado
- **WHEN** una reserva con inicio libre y duración válida incumple el horario diario, anticipación, disponibilidad o límite acumulado consecutivo de cuatro horas
- **THEN** el sistema rechaza la reserva con la causa correspondiente y no registra una operación exitosa
