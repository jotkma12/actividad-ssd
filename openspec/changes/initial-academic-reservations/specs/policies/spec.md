# Spec Delta

## Purpose

Define los límites temporales comunes a las reservas y la regla de aprobación de cada espacio. Los valores de esta primera versión convierten en criterios comprobables las reglas propuestas para el proyecto.

## ADDED Requirements

### Requirement: Reservar en bloques de 30 minutos
El sistema SHALL requerir que el inicio y el fin de cada reserva coincidan con bloques de 30 minutos. No se establece un máximo independiente de duración; el horario diario permitido sigue aplicando.

#### Scenario: Reserva de más de cuatro horas dentro del horario
- **WHEN** una reserva dura cinco horas, comienza a las 07:00 y termina a las 12:00
- **THEN** el sistema no la rechaza por superar cuatro horas

#### Scenario: Reserva que usa toda la jornada permitida
- **WHEN** una reserva va de las 07:00 a las 21:00 de un día permitido
- **THEN** el sistema acepta su duración si también cumple las demás políticas y está disponible

#### Scenario: Inicio o fin fuera de un bloque
- **WHEN** la hora de inicio o de finalización no coincide con un bloque de 30 minutos
- **THEN** el sistema rechaza la reserva

#### Scenario: Duración no alineada a bloques
- **WHEN** la duración de una reserva no es múltiplo de 30 minutos
- **THEN** el sistema rechaza la reserva
### Requirement: Limitar horario semanal
El sistema SHALL permitir reservas de lunes a sábado entre las 07:00 y las 21:00, según la zona `America/Bogota`.

#### Scenario: Reserva dentro del horario
- **WHEN** una reserva empieza y termina el mismo día entre las 07:00 y las 21:00, con fin no posterior a las 21:00
- **THEN** el horario cumple esta política

#### Scenario: Reserva fuera del horario o en domingo
- **WHEN** una reserva empieza antes de las 07:00, termina después de las 21:00 o cae en domingo
- **THEN** el sistema la rechaza por horario no permitido

#### Scenario: Reserva que cruza medianoche
- **WHEN** una reserva comienza un día y termina en el siguiente
- **THEN** el sistema la rechaza por exceder el horario diario permitido

#### Scenario: Intervalo con inicio no anterior al fin
- **WHEN** una reserva tiene hora de inicio igual o posterior a la hora de fin
- **THEN** el sistema rechaza el intervalo

### Requirement: Limitar anticipación de reserva
El sistema SHALL exigir que el inicio de una reserva ocurra al menos 24 horas y como máximo 30 días después del momento de la solicitud.

#### Scenario: Inicio dentro del rango permitido
- **WHEN** el inicio ocurre entre 24 horas y 30 días desde la solicitud, incluidos ambos límites
- **THEN** la anticipación cumple esta política

#### Scenario: Anticipación insuficiente
- **WHEN** el inicio ocurre menos de 24 horas después de la solicitud
- **THEN** el sistema rechaza la reserva por anticipación insuficiente

#### Scenario: Anticipación excesiva
- **WHEN** el inicio ocurre más de 30 días después de la solicitud
- **THEN** el sistema rechaza la reserva por anticipación excesiva

### Requirement: Usar la hora de Colombia
El sistema SHALL interpretar y validar los horarios de reserva en `America/Bogota` y conservar los momentos con el formato uniforme definido por el plan de ingeniería.

#### Scenario: Validar horario local
- **WHEN** una persona envía una fecha y hora local para reservar
- **THEN** el sistema evalúa el día, la hora y la anticipación usando `America/Bogota`

### Requirement: Configurar aprobación por espacio
El sistema SHALL requerir que cada espacio tenga configurado si sus reservas requieren aprobación.

#### Scenario: Espacio configurado para aprobación
- **WHEN** un administrador establece si un espacio requiere aprobación
- **THEN** el sistema conserva esa regla para las nuevas reservas del espacio

#### Scenario: Regla de aprobación no configurada
- **WHEN** se intenta habilitar un espacio para reservas sin que tenga definida su regla de aprobación
- **THEN** el sistema rechaza la operación hasta que un administrador configure la regla

#### Scenario: Cambiar regla de aprobación
- **WHEN** un administrador cambia la regla de aprobación de un espacio
- **THEN** la nueva regla se aplica a las nuevas reservas y no cambia automáticamente el estado de reservas existentes

