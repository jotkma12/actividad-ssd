# Spec Delta

## Purpose

Define cómo las personas acceden a la aplicación web y cómo la interfaz presenta las funciones permitidas para su cuenta autenticada.

## ADDED Requirements

### Requirement: Iniciar sesión con el servicio institucional
La interfaz SHALL solicitar correo institucional y contraseña y SHALL autenticar las credenciales mediante el servicio real del sistema.

#### Scenario: Acceso correcto
- **WHEN** una persona envía credenciales válidas de una cuenta activa
- **THEN** la interfaz abre la página principal con la identidad y el rol que devuelve el servicio

#### Scenario: Credenciales inválidas o cuenta inactiva
- **WHEN** el servicio rechaza las credenciales o la cuenta está inactiva
- **THEN** la interfaz permanece en el formulario y muestra el error recibido sin abrir una sesión

#### Scenario: Servicio de autenticación no disponible
- **WHEN** no se puede contactar el servicio de autenticación
- **THEN** la interfaz informa que no fue posible conectar y conserva el formulario para reintentar

### Requirement: Presentar página principal según el rol autenticado
La interfaz SHALL mostrar el rol devuelto por el servicio y un resumen obtenido de los endpoints permitidos para ese rol, sin presentar datos de demostración ni sustituir la autorización del backend.

#### Scenario: Resumen de solicitante
- **WHEN** inicia sesión una cuenta con rol solicitante
- **THEN** la página principal presenta el rol, los totales reales de reservas pendientes y aprobadas y las áreas disponibles para el solicitante

#### Scenario: Resumen de aprobador
- **WHEN** inicia sesión una cuenta con rol aprobador
- **THEN** la página principal presenta el rol y los totales reales de solicitudes y cambios pendientes de sus espacios asignados

#### Scenario: Resumen de administrador
- **WHEN** inicia sesión una cuenta con rol administrador
- **THEN** la página principal presenta el rol y los totales reales de espacios y cuentas que devuelve el servicio

### Requirement: Cerrar la sesión autenticada
La interfaz SHALL permitir cerrar la sesión y retirar el acceso a las vistas protegidas.

#### Scenario: Cierre de sesión
- **WHEN** una persona autenticada selecciona cerrar sesión
- **THEN** la interfaz solicita el cierre al servicio, elimina el estado de sesión local y vuelve al formulario de acceso
