# Spec Delta

## Purpose

Define la revisión visual de solicitudes y cambios por aprobadores autorizados para los espacios que tienen asignados.

## ADDED Requirements

### Requirement: Consultar decisiones pendientes asignadas
La interfaz SHALL cargar las solicitudes y cambios pendientes desde las bandejas del servicio autorizado.

#### Scenario: Aprobador consulta su bandeja
- **WHEN** un aprobador abre la bandeja de decisiones
- **THEN** la interfaz muestra solo las solicitudes y cambios devueltos para sus espacios asignados

#### Scenario: Rol distinto intenta abrir decisiones
- **WHEN** una cuenta que no es aprobadora abre una sección de decisiones
- **THEN** la interfaz no presenta controles de aprobación y el servicio conserva la autoridad para denegar la operación

### Requirement: Aprobar o rechazar una solicitud
La interfaz SHALL enviar la decisión elegida al servicio y SHALL exigir un motivo no vacío para rechazar.

#### Scenario: Aprobar una solicitud pendiente
- **WHEN** el aprobador asignado confirma la aprobación de una solicitud vigente
- **THEN** la interfaz muestra el estado confirmado por el servicio

#### Scenario: Rechazar con motivo
- **WHEN** el aprobador asignado ingresa un motivo y confirma el rechazo
- **THEN** la interfaz envía el motivo y muestra el resultado confirmado por el servicio

#### Scenario: Rechazo sin motivo
- **WHEN** el aprobador intenta rechazar sin escribir un motivo
- **THEN** la interfaz indica que el motivo es obligatorio y no envía la decisión

#### Scenario: Solicitud ya vencida o resuelta
- **WHEN** el servicio rechaza una decisión porque la solicitud venció o ya fue resuelta
- **THEN** la interfaz actualiza la bandeja y comunica que la decisión no se aplicó

### Requirement: Resolver cambios de horario pendientes
La interfaz SHALL presentar el horario original y el propuesto y SHALL enviar la decisión al servicio sin sustituir localmente el horario confirmado.

#### Scenario: Aprobar cambio permitido
- **WHEN** el aprobador asignado aprueba un cambio que cumple las reglas vigentes
- **THEN** la interfaz presenta el intervalo nuevo devuelto por el servicio

#### Scenario: Cambio excede la duración permitida
- **WHEN** el servicio impide aprobar un cambio que excede cuatro horas consecutivas
- **THEN** la interfaz conserva y muestra el intervalo original aprobado y comunica que la aprobación no se aplicó

#### Scenario: Rechazar cambio
- **WHEN** el aprobador asignado rechaza un cambio con motivo
- **THEN** la interfaz muestra la reserva original aprobada y confirma el resultado del servicio
