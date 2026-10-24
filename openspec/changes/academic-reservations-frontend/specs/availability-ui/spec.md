# Spec Delta

## Purpose

Define la consulta visual de disponibilidad para que las personas elijan espacios y horarios con información actual del sistema.

## ADDED Requirements

### Requirement: Consultar disponibilidad con datos del sistema
La interfaz SHALL consultar el servicio de disponibilidad para la fecha, hora y espacios seleccionados y SHALL presentar los estados devueltos.

#### Scenario: Mostrar resultados de disponibilidad
- **WHEN** una persona autenticada consulta un intervalo válido
- **THEN** la interfaz muestra en una tabla cada espacio consultado con el estado disponible, ocupado o bloqueado devuelto por el servicio

#### Scenario: Consultar un intervalo inválido
- **WHEN** la persona envía fechas u horas inválidas o contrarias a las políticas
- **THEN** la interfaz muestra el error del servicio y no marca el intervalo como disponible

#### Scenario: Servicio de disponibilidad no responde
- **WHEN** falla la consulta de uno o más espacios
- **THEN** la interfaz informa que no pudo confirmar esos resultados y permite reintentar

### Requirement: Acceder a una solicitud desde un espacio disponible
La interfaz SHALL permitir iniciar una solicitud de reserva para un espacio cuyo intervalo haya sido confirmado como disponible.

#### Scenario: Seleccionar espacio disponible
- **WHEN** el servicio confirma que un espacio está disponible para el intervalo consultado
- **THEN** la interfaz permite abrir el formulario de solicitud con ese espacio e intervalo seleccionados

#### Scenario: Espacio ocupado o bloqueado
- **WHEN** el servicio informa que un espacio está ocupado o bloqueado
- **THEN** la interfaz no ofrece iniciar una solicitud para ese resultado
