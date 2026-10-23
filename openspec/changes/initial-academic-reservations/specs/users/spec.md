# Spec Delta

## Purpose

Permite identificar a las personas que usan el sistema y administrar sus cuentas. Las cuentas y su actividad se conservan para mantener la responsabilidad y el historial de las operaciones.

## ADDED Requirements

### Requirement: Crear cuentas de usuario
El sistema SHALL permitir que solo un administrador cree cuentas con nombre completo, correo institucional, identificación, contraseña y un rol principal.

#### Scenario: Administrador crea cuenta válida
- **WHEN** un administrador registra una persona con todos los datos requeridos y únicos
- **THEN** el sistema crea la cuenta con el rol principal indicado

#### Scenario: Rechazar datos duplicados o incompletos
- **WHEN** un administrador registra una cuenta con datos requeridos ausentes o con correo institucional o identificación ya usados
- **THEN** el sistema rechaza la creación e identifica el dato que debe corregirse

#### Scenario: No existe registro público
- **WHEN** una persona no autenticada intenta crear su propia cuenta
- **THEN** el sistema rechaza la solicitud y no crea una cuenta

### Requirement: Administrar datos de usuario
El sistema SHALL permitir a un administrador actualizar los datos de una cuenta existente sin reemplazar la identidad asociada a su historial.

#### Scenario: Actualizar datos de cuenta
- **WHEN** un administrador guarda datos válidos para una cuenta existente
- **THEN** el sistema actualiza los datos y conserva las operaciones previas asociadas a esa cuenta

### Requirement: Activar y desactivar cuentas
El sistema SHALL permitir a un administrador activar o desactivar una cuenta de usuario.

#### Scenario: Desactivar cuenta
- **WHEN** un administrador desactiva una cuenta activa
- **THEN** el sistema impide que esa cuenta inicie sesión o cree nuevas reservas
- **AND** conserva la cuenta y su historial

#### Scenario: Cuenta desactivada intenta iniciar sesión
- **WHEN** una cuenta desactivada presenta credenciales válidas para iniciar sesión
- **THEN** el sistema deniega el acceso

#### Scenario: Reactivar cuenta
- **WHEN** un administrador activa una cuenta desactivada
- **THEN** el sistema permite que vuelva a iniciar sesión, sujeto a sus credenciales y permisos
