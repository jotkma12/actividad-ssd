# Spec Delta

## Purpose

Define quién puede realizar cada operación del sistema según su rol y, para los aprobadores, según los espacios asignados. Las operaciones no autorizadas se rechazan sin cambiar los datos.

## ADDED Requirements

### Requirement: Asignar un rol principal
El sistema SHALL mantener un único rol principal por usuario entre administrador, solicitante y aprobador.

#### Scenario: Asignar o cambiar rol
- **WHEN** un administrador asigna o cambia el rol principal de una cuenta
- **THEN** el sistema conserva exactamente un rol principal para esa cuenta

#### Scenario: Rechazar cambio de rol no autorizado
- **WHEN** un usuario que no es administrador intenta asignar o cambiar un rol
- **THEN** el sistema rechaza la operación y no cambia el rol

### Requirement: Restringir operaciones administrativas
El sistema SHALL permitir únicamente a los administradores gestionar cuentas, roles, espacios, configuración de aprobación y bloqueos de mantenimiento.

#### Scenario: Usuario sin rol administrativo intenta administrar
- **WHEN** un solicitante o aprobador intenta una operación administrativa
- **THEN** el sistema rechaza la operación y conserva los datos sin cambios

### Requirement: Restringir acciones del solicitante
El sistema SHALL permitir a un solicitante crear y gestionar únicamente sus propias reservas, con las reglas de estado y plazo definidas para reservas.

#### Scenario: Solicitante consulta una reserva ajena
- **WHEN** un solicitante intenta consultar o modificar una reserva que pertenece a otra persona
- **THEN** el sistema rechaza la operación y no revela ni cambia la reserva ajena

### Requirement: Limitar aprobadores a espacios asignados
El sistema SHALL permitir a un aprobador gestionar solicitudes únicamente de espacios que tenga asignados.

#### Scenario: Administrador asigna aprobador a espacio
- **WHEN** un administrador asigna o retira un aprobador de un espacio
- **THEN** el sistema actualiza la asignación para las decisiones futuras

#### Scenario: Usuario no administrador intenta cambiar asignación
- **WHEN** un usuario que no es administrador intenta asignar un aprobador a un espacio
- **THEN** el sistema rechaza la operación y conserva la asignación actual

#### Scenario: Aprobador decide solicitud de espacio asignado
- **WHEN** un aprobador gestiona una solicitud de un espacio que tiene asignado
- **THEN** el sistema autoriza la operación si se cumplen también las reglas del estado de la reserva

#### Scenario: Aprobador decide solicitud de espacio no asignado
- **WHEN** un aprobador intenta gestionar una solicitud de un espacio que no tiene asignado
- **THEN** el sistema rechaza la operación y no cambia la solicitud

### Requirement: Impedir la aprobación propia
El sistema SHALL impedir que una persona apruebe o rechace su propia solicitud de reserva.

#### Scenario: Aprobador es también solicitante de la reserva
- **WHEN** un aprobador intenta decidir una reserva creada por su propia cuenta
- **THEN** el sistema rechaza la decisión y mantiene el estado de la reserva

### Requirement: Rechazar acciones sin permiso
El sistema SHALL comprobar los permisos en cada operación protegida y denegar las acciones no autorizadas.

#### Scenario: Cuenta sin sesión intenta una operación protegida
- **WHEN** una persona sin sesión intenta una operación que requiere autenticación
- **THEN** el sistema deniega la operación y no modifica datos

#### Scenario: Cuenta desactivada intenta una operación protegida
- **WHEN** una cuenta desactivada intenta usar una operación protegida
- **THEN** el sistema deniega la operación y no modifica datos

### Requirement: Limitar la consulta de reservas e historial por rol
El sistema SHALL limitar los datos de reservas e historial visibles según el rol y la asignación de espacios.

#### Scenario: Administrador consulta registros
- **WHEN** un administrador consulta reservas o historial
- **THEN** el sistema muestra los registros de todos los espacios

#### Scenario: Solicitante consulta registros propios
- **WHEN** un solicitante consulta reservas o historial
- **THEN** el sistema muestra únicamente sus reservas y los eventos asociados a ellas

#### Scenario: Aprobador consulta registros asignados
- **WHEN** un aprobador consulta solicitudes o historial
- **THEN** el sistema muestra únicamente registros de espacios que tiene asignados

#### Scenario: Usuario intenta consultar registros ajenos
- **WHEN** un usuario intenta consultar registros fuera del alcance de su rol
- **THEN** el sistema deniega la consulta y no revela esos datos