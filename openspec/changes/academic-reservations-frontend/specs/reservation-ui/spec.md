# Spec Delta

## Purpose

Define la gestión visual de solicitudes y reservas propias, respetando estados, políticas y decisiones que aplica el backend.

## ADDED Requirements

### Requirement: Solicitar una reserva
La interfaz SHALL enviar al servicio real el espacio y el intervalo elegidos y SHALL presentar el estado que el sistema asigne.

#### Scenario: Solicitud aceptada
- **WHEN** el solicitante envía un intervalo disponible y conforme a las políticas
- **THEN** la interfaz muestra la reserva devuelta con estado pendiente o aprobada según la configuración del espacio

#### Scenario: Solicitud rechazada por política o conflicto
- **WHEN** el servicio rechaza una solicitud por horario, anticipación, duración, disponibilidad o estado del espacio
- **THEN** la interfaz muestra el motivo y no agrega una reserva como si se hubiera creado

### Requirement: Consultar y modificar reservas propias
La interfaz SHALL mostrar las reservas autorizadas por el servicio y SHALL ofrecer modificación solo cuando corresponda al estado y plazo vigentes.

#### Scenario: Consultar reservas propias
- **WHEN** un solicitante abre sus reservas
- **THEN** la interfaz muestra los registros recibidos del servicio con sus estados y horarios

#### Scenario: Modificar reserva permitida
- **WHEN** el solicitante envía un cambio permitido
- **THEN** la interfaz muestra el resultado real, incluida una solicitud pendiente de aprobación cuando corresponda

#### Scenario: Modificación rechazada
- **WHEN** el servicio rechaza una modificación por plazo, disponibilidad o límite acumulado
- **THEN** la interfaz mantiene visibles los datos originales confirmados por el servicio y comunica el motivo

### Requirement: Cancelar reservas propias
La interfaz SHALL solicitar confirmación antes de cancelar una reserva y SHALL mostrar el resultado del servicio.

#### Scenario: Cancelación permitida
- **WHEN** el solicitante confirma una cancelación permitida para la reserva
- **THEN** la interfaz presenta el estado cancelado devuelto por el servicio

#### Scenario: Cancelación fuera de plazo o no permitida
- **WHEN** el servicio rechaza la cancelación
- **THEN** la interfaz conserva el estado de reserva previo y muestra el motivo del rechazo
