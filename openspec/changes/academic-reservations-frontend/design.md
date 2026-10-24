# Design

## Context

El backend es una aplicación modular FastAPI con SQLite y endpoints protegidos por bearer token. React 19 y Vite ya están instalados, pero `App.jsx` solo contiene una pantalla inicial. No hay capacidades publicadas en `openspec/specs/`; las reglas de dominio están en los cambios completos `initial-academic-reservations` y `enforce-four-hour-reservation-limit`. Se mantienen como contratos de referencia.

## Goals / Non-Goals

**Goals:**

- Entregar la interfaz en módulos pequeños, cada uno con pruebas Playwright y una propuesta de commit separada.
- Hacer que las pantallas consulten y modifiquen los datos reales del backend y mostrar los errores que este devuelve.
- Conservar los permisos y políticas del servidor como autoridad final.
- Cubrir en la interfaz las siete áreas identificadas en `proposal.md`.

**Non-Goals:**

- Cambiar FastAPI, SQLite, React, Vite, pytest o Playwright por otras tecnologías.
- Crear servicios separados, una aplicación móvil, notificaciones automáticas o datos de demostración.
- Duplicar en React las validaciones de autorización o disponibilidad que ya impone el backend.
- Añadir funciones de reportes no requeridas por las especificaciones.

## Decisions

### Cliente API y ejecución

Las vistas usarán un cliente HTTP compartido con una URL base configurable mediante `VITE_API_BASE_URL`. En desarrollo, Vite expondrá `/api` y lo reenviará a FastAPI, retirando ese prefijo antes de enviar la petición. Esto permite ejecutar frontend y backend en sus puertos previstos sin cambiar CORS ni agregar servicios. Para una distribución distinta, la URL base se configurará por entorno.

Se conserva la navegación dentro de React sin instalar un router adicional. El estado de sesión mantiene el bearer token en memoria y lo agrega a cada solicitud protegida; no se guarda en almacenamiento persistente del navegador. Al recargar la página se solicita iniciar sesión de nuevo. Se elige esta alternativa para no prolongar la vida del token en almacenamiento accesible a scripts; el backend actual no usa cookies HttpOnly.

### Autorización y datos

El rol devuelto por `/auth/login` determina qué secciones presenta la interfaz. Cada operación seguirá enviándose al endpoint protegido correspondiente: ocultar una acción en React mejora la navegación, pero no sustituye la autorización del backend. Las listas y estados solo se muestran después de una respuesta real; los errores de red, autenticación o validación se distinguen de listas vacías.

La consulta tabular de disponibilidad obtiene los espacios y consulta el endpoint vigente por espacio para el intervalo elegido. No se añade una ruta agregada ni se relajan las reglas del servidor. El ciclo de reservas utiliza los endpoints existentes de creación, consulta, modificación, cancelación y aprobación.

La especificación existente de usuarios exige editar datos, pero no hay endpoint para hacerlo. El módulo de usuarios añadirá una actualización transaccional de nombre completo, correo institucional e identificación, validará unicidad y dominio y registrará el cambio en historial. El rol seguirá gestionándose por su operación específica; este cambio no añade edición de contraseña.

### Pruebas y separación por módulos

Playwright será el ejecutor de recorridos de navegador previsto por el plan. Las pruebas arrancarán FastAPI y Vite y usarán una base SQLite desechable con cuentas sembradas para las pruebas; no interceptarán el API con respuestas falsas. Cada grupo de módulo terminará sus pruebas y documentación antes de avanzar. Los límites de módulo permitirán proponer commits independientes sin incluir cambios anteriores ajenos.

## Risks / Trade-offs

- [Una respuesta de disponibilidad por espacio puede aumentar las solicitudes] → Consultar únicamente espacios visibles y estados necesarios; mantener el endpoint existente y medir antes de proponer una API agregada.
- [La sesión en memoria se pierde al recargar] → Mantener explícito el comportamiento y requerir un nuevo inicio de sesión; no almacenar bearer tokens en almacenamiento web persistente.
- [Un endpoint de actualización de cuentas puede romper la unicidad] → Validar correo e identificación dentro de `BEGIN IMMEDIATE`, mantener la identidad de usuario y registrar el evento en historial.
- [Las pruebas de navegador dependen de que Chrome esté instalado localmente] → Configurar Playwright para usar el canal `chrome` y documentar ese requisito sin descargar otro navegador.

## Migration Plan

No se requiere migración de SQLite para las vistas. El endpoint pendiente de actualización de cuentas usa columnas existentes. En desarrollo se iniciarán FastAPI y Vite por separado y se conectarán mediante el proxy `/api`.

## Open Questions

No hay decisiones de negocio pendientes para el primer módulo. La actualización de cuenta se limita a nombre, correo e identificación, de acuerdo con los datos de perfil existentes; el rol usa su operación definida y no se añadirá cambio de contraseña administrativo.
