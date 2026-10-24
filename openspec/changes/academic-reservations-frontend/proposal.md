# Proposal

## Why

El backend FastAPI ya ofrece los flujos principales de cuentas, espacios y reservas, pero el React actual solo muestra una pantalla de bienvenida y no permite utilizar esos flujos. Se necesita una interfaz conectada al API real para que cada rol pueda operar el sistema conforme a las especificaciones y revisar sus resultados.

## What Changes

- Reemplazar la pantalla inicial por inicio de sesión y una página principal que presente funciones acordes con el rol autenticado.
- Añadir vistas de administración de espacios y cuentas, incluyendo roles, activación y asignación de aprobadores.
- Añadir consulta tabular de disponibilidad, solicitudes y consulta de reservas, modificaciones y cancelaciones.
- Añadir bandejas de aprobación y rechazo, incluida la decisión sobre cambios de horario.
- Añadir consulta del historial según el alcance permitido por el backend.
- Conectar las vistas a los endpoints existentes mediante una configuración de API reutilizable; mostrar estados de carga, errores y resultados del servidor.
- Añadir las pruebas de interfaz con Playwright definidas por el plan y recorridos contra el backend real.
- Añadir una operación de actualización de datos de cuenta solo si se requiere para cumplir la especificación existente de administración de usuarios, con validación y pruebas del backend.

## Capabilities

### New Capabilities

- `authentication-ui`: inicio y cierre de sesión y entrada al área de trabajo según el rol devuelto por el API.
- `space-management-ui`: consulta y administración de espacios y bloqueos permitidos.
- `user-administration-ui`: consulta de cuentas, creación, edición, activación, cambio de rol y asignación de aprobadores.
- `availability-ui`: consulta tabular de espacios disponibles, ocupados y bloqueados.
- `reservation-ui`: solicitud, consulta, modificación y cancelación de reservas propias.
- `approval-ui`: bandejas y decisiones para solicitudes y cambios asignados.
- `history-ui`: consulta de eventos permitidos por el rol.

### Modified Capabilities

No hay capacidades publicadas en `openspec/specs/`. Estas capacidades de interfaz complementan los requisitos funcionales definidos en `initial-academic-reservations`; no cambian las reglas de negocio de reservas ni permisos.

## Impact

El trabajo afecta `frontend/src/App.jsx`, `frontend/src/style.css`, nuevos módulos de API y vistas, la configuración de Vite para conectar el servidor React con FastAPI durante desarrollo, y pruebas Playwright. El backend actual proporciona endpoints de autenticación, cuentas, espacios, disponibilidad, reservas, aprobaciones e historial. La especificación de usuarios contempla editar datos de cuenta, pero el API actual no ofrece esa operación; se deberá añadirla con sus pruebas antes de habilitar esa acción en la interfaz. La base SQLite y la arquitectura modular monolítica permanecen sin cambios. No se introducirán bibliotecas de componentes ni otro framework de interfaz.
