# Spec Delta

## Purpose

Permite solicitar el uso de espacios y gestionar cada reserva durante su ciclo de vida. Las decisiones de aprobación, cambios y cancelaciones conservan el estado y la responsabilidad de quien actuó.

## ADDED Requirements

### Requirement: Conservar los estados de las reservas
El sistema SHALL representar cada reserva con exactamente uno de estos estados: pendiente, aprobada, rechazada, rechazada por vencimiento, cancelada o finalizada.

#### Scenario: Finalizar reserva aprobada vencida
- **WHEN** el sistema evalúa una reserva aprobada cuyo fin ya ocurrió
- **THEN** el sistema cambia su estado a finalizada

#### Scenario: Estados cerrados no se reabren
- **WHEN** una operación ordinaria intenta cambiar una reserva rechazada, rechazada por vencimiento, cancelada o finalizada
- **THEN** el sistema rechaza el cambio y conserva el estado

#### Scenario: Rechazo por vencimiento libera el intervalo
- **WHEN** una reserva pasa a rechazada por vencimiento al llegar su hora de inicio
- **THEN** deja de ocupar el horario para nuevas consultas y solicitudes, salvo que otra reserva o bloqueo lo ocupe
### Requirement: Crear una reserva
El sistema SHALL permitir a un solicitante activo crear una reserva para un espacio activo cuando el horario cumple las políticas y está disponible.

#### Scenario: Crear reserva sin aprobación requerida
- **WHEN** un solicitante activo pide un horario válido y disponible en un espacio que no requiere aprobación
- **THEN** el sistema crea la reserva en estado aprobada

#### Scenario: Crear reserva que requiere aprobación
- **WHEN** un solicitante activo pide un horario válido y disponible en un espacio que requiere aprobación
- **THEN** el sistema crea la reserva en estado pendiente

#### Scenario: Solicitar espacio desactivado
- **WHEN** un solicitante intenta crear una reserva para un espacio desactivado
- **THEN** el sistema rechaza la solicitud y no crea una reserva

#### Scenario: Cuenta desactivada intenta reservar
- **WHEN** una cuenta desactivada intenta crear una reserva
- **THEN** el sistema rechaza la solicitud y no crea una reserva

#### Scenario: Horario inválido o no disponible
- **WHEN** una solicitud incumple una política o su horario no está disponible
- **THEN** el sistema rechaza la solicitud, informa la causa y no crea una reserva incompatible

### Requirement: Consultar reservas
El sistema SHALL permitir consultar reservas según los permisos del usuario y mostrar sus datos, horario, espacio y estado.

#### Scenario: Solicitante consulta sus reservas
- **WHEN** un solicitante consulta sus reservas
- **THEN** el sistema muestra las reservas asociadas a su cuenta y sus estados actuales

#### Scenario: Usuario consulta una reserva fuera de su alcance
- **WHEN** un usuario intenta consultar una reserva que no puede ver según su rol
- **THEN** el sistema deniega la consulta sin revelar los datos de la reserva

### Requirement: Modificar reservas pendientes
El sistema SHALL permitir al solicitante modificar sus reservas pendientes antes de que sean resueltas, sujeto a las políticas y a la disponibilidad del nuevo horario.

#### Scenario: Modificar reserva pendiente
- **WHEN** el solicitante modifica su reserva pendiente antes de una decisión y el nuevo horario es válido y disponible
- **THEN** el sistema guarda los nuevos datos y mantiene el estado pendiente

#### Scenario: Modificar reserva pendiente no propia o ya resuelta
- **WHEN** un solicitante intenta modificar una reserva ajena o que ya no está pendiente
- **THEN** el sistema rechaza la operación y conserva la reserva sin cambios

#### Scenario: Nuevo horario inválido o no disponible
- **WHEN** una modificación pendiente incumple una política o el nuevo horario no está disponible
- **THEN** el sistema rechaza la modificación y conserva los datos previos

### Requirement: Modificar reservas aprobadas
El sistema SHALL permitir al solicitante modificar una reserva aprobada hasta dos horas antes de su inicio, sujeto a políticas y disponibilidad.

#### Scenario: Modificar reserva aprobada sin nueva aprobación
- **WHEN** el solicitante modifica una reserva aprobada dentro del plazo permitido y el espacio no requiere aprobación
- **THEN** el sistema guarda el cambio si el nuevo horario cumple las políticas y está disponible

#### Scenario: Modificar reserva aprobada que requiere nueva aprobación
- **WHEN** el solicitante modifica dentro del plazo permitido una reserva aprobada de un espacio que requiere aprobación
- **THEN** el sistema solicita una nueva aprobación antes de confirmar los datos modificados

#### Scenario: Intentar modificar fuera del plazo
- **WHEN** el solicitante intenta modificar una reserva aprobada a menos de dos horas de su inicio
- **THEN** el sistema rechaza la modificación y conserva la reserva sin cambios

#### Scenario: Modificación rechazada por horario inválido o ocupado
- **WHEN** una modificación de reserva aprobada incumple una política o su nuevo horario no está disponible
- **THEN** el sistema rechaza la modificación y conserva los datos previos

#### Scenario: Cambio aprobado requiere autorización
- **WHEN** una reserva aprobada pertenece a un espacio que requiere aprobación y el solicitante pide un nuevo horario válido y disponible
- **THEN** la reserva original permanece aprobada y ocupa su intervalo mientras el nuevo intervalo queda bloqueado provisionalmente
- **AND** el cambio requiere una decisión de un aprobador asignado antes de sustituir el horario original

#### Scenario: Cambio aprobado es rechazado
- **WHEN** un aprobador asignado rechaza el cambio pendiente de una reserva aprobada
- **THEN** el sistema libera el nuevo intervalo provisional y conserva aprobada la reserva con las fechas y horas originales

#### Scenario: Se cancela la reserva original mientras espera el cambio
- **WHEN** el solicitante o un administrador cancela la reserva original mientras tiene un cambio pendiente
- **THEN** el sistema cancela también el cambio pendiente y libera su intervalo provisional

### Requirement: Cancelar reservas
El sistema SHALL permitir cancelar reservas según el rol, el estado y el plazo de cancelación aplicable.

#### Scenario: Solicitante cancela reserva pendiente
- **WHEN** el solicitante cancela su reserva pendiente antes de que se resuelva
- **THEN** el sistema cambia su estado a cancelada

#### Scenario: Solicitante cancela reserva aprobada dentro del plazo
- **WHEN** el solicitante cancela su reserva aprobada con al menos dos horas antes de su inicio
- **THEN** el sistema cambia su estado a cancelada

#### Scenario: Solicitante intenta cancelar reserva aprobada fuera del plazo
- **WHEN** el solicitante intenta cancelar su reserva aprobada a menos de dos horas de su inicio
- **THEN** el sistema rechaza la cancelación y conserva el estado aprobado

#### Scenario: Administrador cancela reserva con motivo
- **WHEN** un administrador cancela una reserva pendiente o aprobada e indica un motivo
- **THEN** el sistema cambia su estado a cancelada y conserva el motivo

#### Scenario: Administrador intenta cancelar sin motivo
- **WHEN** un administrador intenta cancelar una reserva pendiente o aprobada sin motivo
- **THEN** el sistema rechaza la operación y mantiene la reserva sin cambios

#### Scenario: Solicitante cancela con motivo opcional
- **WHEN** un solicitante cancela una reserva propia dentro de las condiciones permitidas, con o sin motivo
- **THEN** el sistema cambia su estado a cancelada y conserva el motivo si fue proporcionado

#### Scenario: Usuario intenta cancelar una reserva no cancelable
- **WHEN** un usuario intenta cancelar una reserva ajena, rechazada, cancelada o finalizada
- **THEN** el sistema rechaza la operación y conserva el estado

### Requirement: Conservar los registros de reserva
El sistema SHALL conservar las reservas rechazadas, canceladas y finalizadas en lugar de borrarlas durante las operaciones normales.

#### Scenario: Consultar una reserva cerrada
- **WHEN** una persona autorizada consulta una reserva rechazada, cancelada o finalizada
- **THEN** el sistema muestra el registro con su estado final y conserva su historial
