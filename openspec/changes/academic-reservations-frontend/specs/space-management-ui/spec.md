# Spec Delta

## Purpose

Define las pantallas con las que las personas consultan espacios y los administradores gestionan su información y mantenimiento.

## ADDED Requirements

### Requirement: Consultar espacios académicos
La interfaz SHALL mostrar los espacios y el estado que entrega el servicio real, respetando el alcance de consulta de la cuenta autenticada.

#### Scenario: Consulta de espacios
- **WHEN** una persona autenticada abre la sección de espacios
- **THEN** la interfaz carga y presenta los datos recibidos del servicio

#### Scenario: Error al cargar espacios
- **WHEN** el servicio no responde o devuelve un error
- **THEN** la interfaz informa el error y permite volver a intentar sin mostrar datos ficticios

### Requirement: Administrar espacios como administrador
La interfaz SHALL ofrecer creación, edición, activación, desactivación y configuración de aprobación solo a administradores.

#### Scenario: Administrador guarda cambios de un espacio
- **WHEN** un administrador envía datos válidos para crear o modificar un espacio
- **THEN** la interfaz guarda los datos mediante el servicio y actualiza la vista con la respuesta real

#### Scenario: Desactivar espacio con reservas futuras
- **WHEN** el servicio informa que hay reservas futuras por revisar al desactivar un espacio
- **THEN** la interfaz muestra la cantidad y deja la decisión de mantenerlas o cancelarlas al administrador

#### Scenario: Usuario no administrador intenta administrar espacios
- **WHEN** un solicitante o aprobador intenta acceder a una acción de edición
- **THEN** la interfaz no presenta esa acción y el servicio sigue siendo responsable de rechazar accesos no autorizados

### Requirement: Gestionar bloqueos de mantenimiento
La interfaz SHALL permitir a administradores crear, modificar y retirar bloqueos usando el servicio de espacios.

#### Scenario: Bloqueo válido
- **WHEN** un administrador guarda un bloqueo sin conflictos
- **THEN** la interfaz muestra el bloqueo confirmado por el servicio

#### Scenario: Bloqueo en conflicto con una reserva
- **WHEN** el servicio rechaza un bloqueo que coincide con una reserva pendiente o aprobada
- **THEN** la interfaz informa el conflicto y permite al administrador revisar las reservas afectadas
