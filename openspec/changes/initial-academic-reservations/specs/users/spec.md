# Spec Delta

## Purpose

Permite identificar a las personas que usan el sistema y administrar sus cuentas. Las cuentas y su actividad se conservan para mantener la responsabilidad y el historial de las operaciones.

## ADDED Requirements

### Requirement: Crear cuentas de usuario
El sistema SHALL permitir que solo un administrador cree cuentas con nombre completo, correo institucional, identificación, contraseña de al menos 12 caracteres y un rol principal. Las cuentas creadas por esta vía comenzarán inactivas.

#### Scenario: Administrador crea cuenta válida
- **WHEN** un administrador registra una persona con todos los datos requeridos y únicos, correo terminado en `@universidad.edu.co` y contraseña de al menos 12 caracteres
- **THEN** el sistema crea la cuenta inactiva con el rol principal indicado

#### Scenario: Correo fuera del dominio institucional
- **WHEN** un administrador registra una cuenta cuyo correo no termina en `@universidad.edu.co`
- **THEN** el sistema rechaza la creación e indica que debe usarse el dominio institucional

#### Scenario: Rechazar datos duplicados o incompletos
- **WHEN** un administrador registra una cuenta con datos requeridos ausentes o con correo institucional o identificación ya usados
- **THEN** el sistema rechaza la creación e identifica el dato que debe corregirse

#### Scenario: Rechazar contraseña demasiado corta
- **WHEN** un administrador registra una cuenta con una contraseña de menos de 12 caracteres
- **THEN** el sistema rechaza la creación e indica la longitud mínima requerida

#### Scenario: No existe registro público
- **WHEN** una persona no autenticada intenta crear su propia cuenta
- **THEN** el sistema rechaza la solicitud y no crea una cuenta

### Requirement: Configurar el primer administrador
El sistema SHALL permitir que la configuración inicial cree el primer administrador activo solo cuando aún no exista una cuenta con rol de administrador. La configuración requerirá nombre completo, correo terminado en `@universidad.edu.co` y contraseña de al menos 12 caracteres. No se crearán administradores iniciales automáticamente.

#### Scenario: Crear el primer administrador válido
- **WHEN** se ejecuta la configuración inicial con nombre completo, correo institucional válido y contraseña de al menos 12 caracteres, y no existe un administrador
- **THEN** el sistema crea una cuenta activa con rol de administrador

#### Scenario: Rechazar datos inválidos del administrador inicial
- **WHEN** la configuración inicial omite el nombre, correo o contraseña, usa un correo fuera de `@universidad.edu.co` o proporciona una contraseña de menos de 12 caracteres
- **THEN** el sistema rechaza la configuración e identifica los datos que deben corregirse
- **AND** no crea una cuenta de administrador

#### Scenario: Impedir un segundo administrador inicial
- **WHEN** se ejecuta la configuración inicial y ya existe una cuenta con rol de administrador
- **THEN** el sistema rechaza la configuración
- **AND** no crea otra cuenta de administrador inicial

#### Scenario: No crear automáticamente otro administrador inicial
- **WHEN** el sistema inicia y ya existe un administrador
- **THEN** el sistema conserva las cuentas existentes y no crea otro administrador inicial

#### Scenario: La contraseña inicial debe cumplir la longitud mínima
- **WHEN** se configura el primer administrador con una contraseña de menos de 12 caracteres
- **THEN** el sistema rechaza la configuración sin crear la cuenta
- **AND** acepta cualquier combinación de caracteres si la contraseña tiene al menos 12 caracteres

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
- **AND** conserva las reservas futuras para que el administrador decida si las mantiene o cancela

#### Scenario: Revisar reservas futuras de una cuenta desactivada
- **WHEN** se desactiva una cuenta que tiene reservas futuras
- **THEN** el sistema informa al administrador que debe revisarlas
- **AND** no las cancela automáticamente

#### Scenario: Cuenta desactivada intenta iniciar sesión
- **WHEN** una cuenta desactivada presenta credenciales válidas para iniciar sesión
- **THEN** el sistema deniega el acceso

#### Scenario: Reactivar cuenta
- **WHEN** un administrador activa una cuenta desactivada
- **THEN** el sistema permite que vuelva a iniciar sesión, sujeto a sus credenciales y permisos
