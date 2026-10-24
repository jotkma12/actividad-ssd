# Spec Delta

## Purpose

Conserva un registro consultable de las operaciones importantes para saber quién actuó, cuándo ocurrió y qué información cambió. Los eventos permiten revisar decisiones sin reemplazar los registros actuales de usuarios, espacios y reservas.

## ADDED Requirements

### Requirement: Registrar eventos relevantes
El sistema SHALL registrar cada creación, modificación, activación, desactivación, asignación de rol, asignación de aprobador, aprobación, rechazo, cancelación y cambio de mantenimiento con actor, fecha y hora, entidad, acción y valores anteriores y nuevos de los campos modificados.

#### Scenario: Registrar creación o modificación
- **WHEN** un usuario autorizado crea o modifica un usuario, rol, asignación de aprobador, espacio, reserva o bloqueo
- **THEN** el sistema registra el actor, el momento, la entidad y los valores anteriores y nuevos de los campos modificados

#### Scenario: Registrar decisión de reserva
- **WHEN** una reserva es aprobada, rechazada o cancelada
- **THEN** el sistema registra quién tomó la decisión, cuándo ocurrió y el estado resultante

#### Scenario: Registrar vencimiento automático
- **WHEN** una solicitud pendiente vence al llegar a su hora de inicio
- **THEN** el sistema registra el vencimiento como una acción del sistema, el momento, el estado resultante y el motivo

#### Scenario: Registrar decisión sobre un cambio de horario
- **WHEN** un aprobador autoriza o rechaza un cambio de una reserva aprobada
- **THEN** el sistema registra actor, momento, resultado y los intervalos anterior y propuesto

### Requirement: Conservar motivos de decisiones
El sistema SHALL incluir en el evento el motivo proporcionado para un rechazo o una cancelación cuando corresponda.

#### Scenario: Rechazo con motivo
- **WHEN** una persona autorizada rechaza una solicitud con un motivo
- **THEN** el motivo queda asociado al evento de rechazo

#### Scenario: Cancelación con motivo opcional u obligatorio
- **WHEN** una reserva se cancela con un motivo proporcionado
- **THEN** el evento conserva ese motivo
- **AND** si la cancelación administrativa carece de motivo, la operación se rechaza

### Requirement: Mantener historial asociado
El sistema SHALL conservar los eventos y las relaciones históricas aunque una cuenta se desactive o una reserva cambie de estado.

#### Scenario: Usuario asociado a eventos se desactiva
- **WHEN** se desactiva una cuenta que realizó operaciones previas
- **THEN** sus eventos y la relación con ellos permanecen consultables

#### Scenario: Reserva cambia de estado
- **WHEN** una reserva pasa a aprobada, rechazada o cancelada
- **THEN** el sistema conserva el evento del estado anterior y agrega el nuevo evento

### Requirement: Impedir alterar el historial mediante operaciones normales
El sistema SHALL permitir consultar los eventos según permisos, pero no editar ni borrar eventos mediante las operaciones normales del sistema.

#### Scenario: Usuario autorizado consulta historial
- **WHEN** un usuario con permiso consulta el historial de una entidad
- **THEN** el sistema devuelve los eventos disponibles en orden cronológico con su actor y momento

#### Scenario: Usuario sin permiso consulta historial
- **WHEN** un usuario intenta consultar eventos fuera de su alcance
- **THEN** el sistema deniega la consulta sin revelar los eventos

#### Scenario: Intento de editar o borrar evento
- **WHEN** una persona intenta modificar o eliminar un evento mediante una operación normal
- **THEN** el sistema rechaza la operación y conserva el evento
