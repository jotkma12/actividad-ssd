# Spec Delta

## Purpose

Define cómo el administrador consulta y administra cuentas, roles y asignaciones sin perder la identidad asociada al historial.

## ADDED Requirements

### Requirement: Consultar cuentas de usuario
La interfaz SHALL presentar la lista real de cuentas únicamente a una cuenta administradora.

#### Scenario: Administrador consulta cuentas
- **WHEN** un administrador abre la gestión de usuarios
- **THEN** la interfaz presenta las cuentas devueltas por el servicio, incluidos sus roles y estados

#### Scenario: Usuario sin permiso abre la gestión de usuarios
- **WHEN** un solicitante o aprobador intenta acceder a la gestión de cuentas
- **THEN** la interfaz deniega la sección y no presenta datos de cuentas

### Requirement: Administrar cuentas desde la interfaz
La interfaz SHALL permitir a administradores crear cuentas y editar los datos de cuentas existentes mediante el servicio, mostrando sus validaciones y resultados.

#### Scenario: Crear cuenta
- **WHEN** el administrador envía nombre, correo institucional, identificación, contraseña válida y rol
- **THEN** la interfaz muestra la cuenta creada con estado inactivo

#### Scenario: Corregir datos rechazados
- **WHEN** el servicio rechaza datos duplicados, un correo institucional inválido o una contraseña menor de 12 caracteres
- **THEN** la interfaz muestra el motivo y conserva el formulario para corregirlo

#### Scenario: Editar datos de cuenta
- **WHEN** el administrador guarda cambios válidos en los datos de una cuenta
- **THEN** la interfaz muestra los datos confirmados por el servicio y conserva la identidad de la cuenta

### Requirement: Gestionar estados, roles y asignaciones
La interfaz SHALL permitir a administradores activar o desactivar cuentas, asignar un único rol principal y asignar o retirar aprobadores de espacios.

#### Scenario: Activar o desactivar cuenta
- **WHEN** el administrador cambia el estado de una cuenta
- **THEN** la interfaz muestra el estado confirmado por el servicio y, al desactivarla, informa las reservas futuras que requieren revisión sin cancelarlas

#### Scenario: Cambiar rol o asignar aprobador
- **WHEN** el administrador cambia el rol principal o la asignación de un aprobador a un espacio
- **THEN** la interfaz actualiza la vista con la respuesta del servicio

#### Scenario: Error al cambiar permisos
- **WHEN** el servicio rechaza un cambio de rol o asignación
- **THEN** la interfaz conserva el estado previo y comunica el error
