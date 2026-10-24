# Informe final: sistema de reservas académicas

**Fecha de elaboración:** 24 de octubre de 2026  
**Repositorio:** [jotkma12/actividad-ssd](https://github.com/jotkma12/actividad-ssd)

## 2.1. Introducción

La universidad necesita coordinar el uso de aulas, laboratorios, auditorios y otros espacios académicos. Cuando las solicitudes se administran por correo y hojas de cálculo, resulta más difícil detectar horarios cruzados, aplicar reglas uniformes y saber quién tomó una decisión. El sistema desarrollado centraliza esas operaciones en una aplicación web conectada a una API y una base de datos.

Organizar el trabajo antes de escribir código ayuda a definir qué problema se resolverá, quién usará el sistema, cuáles son las reglas y cómo se comprobará el comportamiento. Este informe resume el proceso que puede respaldarse con el plan, las especificaciones, el código, el historial de Git y las pruebas disponibles. Distingue el alcance implementado de las tareas que siguen abiertas o cuya revisión no puede probarse con los archivos del repositorio.

## 2.2. Descripción general del proyecto

El objetivo general es permitir que una comunidad universitaria consulte la disponibilidad de espacios académicos, solicite su uso y administre las solicitudes de acuerdo con roles y políticas compartidas. Está dirigido a solicitantes, aprobadores responsables de espacios y administradores.

El catálogo admite tipos de espacio como aula, laboratorio o auditorio mediante un campo de tipo; esos ejemplos vienen del plan y del uso del formulario. El tipo se almacena como dato del espacio y no se encontró una lista cerrada de tipos en el esquema.

La solución es una aplicación modular única: FastAPI expone la API, React presenta la interfaz, Vite sirve el frontend en desarrollo y SQLite conserva los datos. Los cambios de esquema se versionan en `backend/migrations/versions/` y se aplican al iniciar la API. El código de acceso a datos utiliza `sqlite3` de Python, sin un ORM declarado en las dependencias.

### Alcance implementado

- Inicio/cierre de sesión, tres roles y operaciones protegidas en la API.
- Gestión de cuentas, espacios, configuración de aprobación y bloqueos de mantenimiento.
- Consulta de disponibilidad y ciclo de reservas, incluidos cambios y cancelaciones.
- Bandejas y decisiones de aprobación, registro histórico y vencimiento automático de solicitudes pendientes.
- Interfaz React conectada a los endpoints reales del backend y pruebas pytest y Playwright.

### Alcance pendiente o fuera de esta versión

No se encontró implementación de reportes de uso, rol directivo/auditor, notificaciones por correo, integración con horarios o notas universitarias, reserva independiente de equipos ni control físico de puertas. Tampoco se encontró una aplicación móvil instalada. Estos puntos coinciden con exclusiones o funcionalidades deseables/condicionales del plan y de la propuesta inicial. El sistema no cuenta con una configuración de despliegue de producción documentada en los archivos inspeccionados.

Las tareas registradas en los cuatro `tasks.md` de cambios de OpenSpec están marcadas completas; eso no demuestra por sí solo que se haya desplegado el sistema o que cada criterio se haya aceptado mediante una revisión humana formal. La lista de comprobación general de cierre en `PLAN_INGENIERIA.md` conserva siete elementos sin marcar; no se modificó ese archivo.

## 2.3. Proceso de planificación de ingeniería

La fuente principal fue [`PLAN_INGENIERIA.md`](PLAN_INGENIERIA.md). El documento plantea como problema las solicitudes repetidas, los cruces de horario, la falta de visibilidad, la dificultad de consultar el historial y la aplicación desigual de reglas.

### Objetivos y requisitos

El plan propone un catálogo de espacios, consulta de disponibilidad, solicitudes sin cruces, aprobaciones, modificaciones y cancelaciones autorizadas, historial, permisos por tipo de usuario y bloqueos de mantenimiento. Como requisitos de calidad propone pruebas unitarias, integración, concurrencia, permisos, recorridos completos y revisión manual de la interfaz; además advierte riesgos como errores de código generado por IA y pérdida de datos.

El plan también contempla una carga inicial moderada —un campus, cientos de espacios y miles de reservas por semestre—, uso de la hora colombiana, historial no destructivo y validación transaccional para reducir conflictos simultáneos. Esos datos son supuestos del plan; no equivalen a pruebas de rendimiento ni a una certificación de capacidad.

### Roles definidos

| Rol | Responsabilidad prevista | Situación en el sistema |
|---|---|---|
| Solicitante | Consultar espacios, crear solicitudes y gestionar las propias según políticas. | Implementado como `requester`. |
| Aprobador | Resolver solicitudes de espacios asignados. | Implementado como `approver`. |
| Administrador | Administrar espacios, cuentas, permisos y mantenimientos. | Implementado como `administrator`. |
| Directivo/auditor | Consultar reportes, según permisos. | No está en los tres roles iniciales de OpenSpec ni en el backend implementado. |

### Reglas de negocio comprobadas en el código

- Las cuentas ordinarias son creadas por un administrador y comienzan inactivas. El primer administrador se crea mediante un comando explícito; no hay credenciales predeterminadas.
- Los correos deben pertenecer al dominio institucional configurado y las contraseñas deben cumplir el mínimo implementado. La aplicación aplica el dominio `@universidad.edu.co` y un mínimo de 12 caracteres.
- Las reservas se interpretan en `America/Bogota`, se normalizan para persistencia en UTC y no cruzan el día. El horario permitido es de lunes a sábado, entre 07:00 y 21:00, con al menos 24 horas y no más de 30 días de anticipación.
- El inicio puede ser cualquier minuto exacto; la duración debe ser un múltiplo de 30 minutos. Una solicitud individual no puede exceder cuatro horas.
- Una secuencia de reservas pendientes/aprobadas contiguas del mismo usuario y espacio tampoco puede superar cuatro horas. Una pausa o un espacio diferente separa los cómputos.
- Los intervalos se comparan con extremos semiabiertos: si uno termina exactamente cuando otro comienza, no hay cruce.
- La cancelación por el solicitante de una reserva aprobada está permitida hasta dos horas antes. El administrador puede cancelar pendientes o aprobadas con motivo.
- Los espacios pueden requerir aprobación; esa configuración determina el estado inicial de nuevas solicitudes. Los cambios posteriores de configuración no reescriben reservas existentes.

### Arquitectura y estrategia

La arquitectura propuesta en el plan es una aplicación modular única con FastAPI, React y SQLite. El código mantiene esos límites por módulos: `usuarios`, `espacios`, `reservas`, `disponibilidad`, `aprobaciones`, `historial` y `politicas`. Para las operaciones críticas de reserva, el servicio consulta y escribe dentro de transacciones SQLite. Las migraciones están en cuatro archivos SQL versionados.

El plan propone trabajar por etapas y relacionar requisitos, especificaciones, tareas y pruebas. El historial de commits muestra implementación por módulos y cambios posteriores de políticas, frontend y pruebas. La lista de cierre del plan, sin embargo, permanece sin marcar y el historial no sustituye una aprobación formal.

## 2.4. Desarrollo dirigido por especificaciones (SDD)

El desarrollo dirigido por especificaciones (SDD, *Spec-Driven Development*) consiste en describir primero el comportamiento esperado y usar esa descripción para orientar el diseño, las tareas, la implementación y las pruebas. No significa que un documento garantice automáticamente que el código esté correcto: hay que comparar el comportamiento y ejecutar verificaciones.

En este repositorio, el plan describe esa secuencia y los cambios de OpenSpec contienen propuestas, diseños, requisitos con escenarios y tareas marcadas. Por ejemplo, la regla acumulada de cuatro horas tiene escenarios para aceptar el límite exacto, rechazar el exceso, reiniciar el cálculo después de una pausa, mantener separados los espacios y conservar datos anteriores. En código, esas decisiones aparecen en `backend/politicas/consecutive.py`, en los servicios de reservas/aprobaciones y en pruebas de reglas/API.

La relación verificable es:

```text
Plan de ingeniería
        ↓
Propuestas y diseños en openspec/changes
        ↓
Requisitos y escenarios por capacidad
        ↓
Tareas verificables
        ↓
Backend / frontend
        ↓
pytest + Playwright + build + validación OpenSpec
```

La evidencia muestra que requisitos nuevos se plasmaron en cambios separados, por ejemplo al introducir el límite de cuatro horas y después permitir inicios a cualquier minuto. El uso de escenarios facilita asociar casos de prueba concretos. No hay métricas del proyecto que permitan cuantificar ahorro de tiempo o reducción de defectos, así que esos beneficios son una valoración del enfoque, no resultados estadísticos.

Una dificultad de mantener SDD es que las reglas y los documentos pueden quedar desalineados. Aquí los cambios están completos, pero los artefactos siguen en `openspec/changes/` y `openspec/specs/` solo contiene `.gitkeep`; por tanto, no se comprobó la sincronización/archivo de las capacidades como especificaciones canónicas. También permanece sin completar la lista general de cierre del plan.

## 2.5. Uso de OpenSpec

OpenSpec organiza los cambios alrededor de artefactos revisables. La configuración de [`openspec/config.yaml`](openspec/config.yaml) declara el esquema `spec-driven` y no añade reglas particulares del proyecto. La estructura encontrada contiene `proposal.md`, `design.md`, `tasks.md` y deltas de especificación bajo `openspec/changes/`.

| Cambio | Capacidades documentadas | Estado de tareas registrado |
|---|---|---|
| `initial-academic-reservations` | `users`, `spaces`, `permissions`, `reservations`, `availability`, `policies`, `approvals`, `history`. | 35 casillas marcadas. |
| `academic-reservations-frontend` | `authentication-ui`, `space-management-ui`, `user-administration-ui`, `availability-ui`, `reservation-ui`, `approval-ui`, `history-ui`. | 8 casillas marcadas. |
| `enforce-four-hour-reservation-limit` | Cambios de `policies`, `reservations` y `approvals`. | 6 casillas marcadas. |
| `arbitrary-start-reservation-durations` | `flexible-reservation-starts`. | 5 casillas marcadas. |

En conjunto hay 54 casillas de tareas y las 54 están marcadas. Los cambios cubren usuarios/permisos, espacios/mantenimiento, políticas, disponibilidad, ciclo de reserva, aprobaciones, historial, interfaz y verificación integrada. Los nombres y escenarios detallados están en las subcarpetas `specs/` de cada cambio.

Se ejecutó la validación estricta de cambios con:

```powershell
openspec.cmd validate --changes --strict
```

Resultado: **4 cambios aprobados, 0 fallidos**. También se intentó validar `openspec/specs/` en estricto; la herramienta informó que no había elementos para validar porque esa carpeta solo tiene `.gitkeep`. La validación estricta verifica la estructura de artefactos, no demuestra por sí sola que la implementación satisfaga cada requisito. No se encontró una salida histórica guardada de validaciones anteriores; este resultado corresponde a la ejecución registrada durante la preparación del informe.

El archivo de trazabilidad [`TRAZABILIDAD_REQUISITOS_PRUEBAS.md`](TRAZABILIDAD_REQUISITOS_PRUEBAS.md) relaciona requisitos con pruebas. Es evidencia de trazabilidad documental; no reemplaza la ejecución de las pruebas que se informa en la sección 2.9.

## 2.6. Uso de Codex

El plan prevé apoyo de IA para preparar borradores, dividir tareas, programar, proponer pruebas, documentar y ayudar a explicar errores. También asigna a la persona responsable la aprobación de reglas, la elección de tecnologías y la revisión del código y resultados.

La conversación de trabajo asociada al repositorio registra solicitudes para continuar la interfaz, completar reservas y aprobaciones, revisar pruebas, documentar la instalación y preparar este informe. La retroalimentación del usuario sirvió para identificar problemas visibles como que el solicitante no encontraba cómo reservar y que el aprobador no veía la bandeja; también pidió permitir inicios en minutos arbitrarios y duraciones en bloques de 30 minutos. Los cambios correspondientes aparecen en los artefactos OpenSpec, el código, las pruebas y el historial de Git.

El historial de Git identifica al autor de los commits como `jotkma12`, no como Codex, y el repositorio no incluye una bitácora versionada de prompts, respuestas del agente ni actas de revisión humana. Por eso, este informe no atribuye cada línea o commit a Codex ni afirma que todo el código generado haya recibido aprobación formal. Los resultados de pruebas, compilación y validación se ejecutaron para este informe en lugar de inferirse de una respuesta del agente.

La herramienta puede acelerar tareas repetitivas de implementación, documentación y elaboración de pruebas. También puede interpretar mal requisitos o introducir errores; por eso la revisión del diff y las pruebas observables siguen siendo necesarias. El repositorio no ofrece una medición del ahorro de tiempo ni del porcentaje de código asistido por IA.

## 2.7. Funcionalidades implementadas

| Módulo / necesidad | Comportamiento implementado | Código principal | Evidencia de pruebas |
|---|---|---|---|
| Autenticación | Inicio/cierre de sesión, cuentas activas y manejo de sesión vencida. El token del frontend vive en memoria. | `backend/usuarios/`; `frontend/src/App.jsx`; `frontend/src/api/client.js`. | `test_users.py`, `test_app.py`; `authentication.spec.js`. |
| Usuarios y permisos | Inicialización de un primer administrador, alta administrativa de cuentas inactivas, edición de datos, activación, rol y asignaciones de aprobadores. | `backend/usuarios/router.py`, `service.py`, `permissions.py`; `frontend/src/UsersPage.jsx`. | `test_users.py`; `users.spec.js`; `role-access.spec.js`. |
| Espacios y mantenimientos | Consulta, creación, edición, estado activo/inactivo, política de aprobación por espacio y bloqueos. Los bloqueos conflictivos se rechazan. | `backend/espacios/`; `frontend/src/SpacesPage.jsx`. | `test_spaces.py`; `spaces.spec.js`. |
| Disponibilidad | Consulta autenticada por espacio e intervalo; distingue disponible, ocupado y bloqueado. | `backend/disponibilidad/`; `frontend/src/AvailabilityPage.jsx`. | `test_availability.py`; `availability.spec.js`. |
| Reservas | Alta, consulta por alcance de rol, modificación y cancelación, con estados, reglas, disponibilidad y concurrencia. | `backend/reservas/`; `frontend/src/ReservationsPage.jsx`; `frontend/src/reservationTime.js`. | `test_reservations.py`, `test_integration_workflow.py`; `reservations.spec.js`. |
| Aprobaciones | Bandejas de solicitudes y cambios por asignación; aprobar o rechazar con motivo. Revalida permisos y políticas al decidir. | `backend/aprobaciones/`; `frontend/src/ApprovalsPage.jsx`. | `test_reservations.py`; `approvals.spec.js`. |
| Historial | Registro de actor, acción y cambios; consulta y filtros conforme al alcance del rol. No hay edición/borrado normal de eventos. | `backend/historial/`; `frontend/src/HistoryPage.jsx`. | `test_history.py`; `history.spec.js`. |
| Interfaz por rol | El panel muestra navegación y acciones según rol, mientras la API vuelve a autorizar cada operación. No hay dependencia de router de React; la navegación entre ventanas usa estado interno. | `frontend/src/App.jsx`, páginas y estilos; dependencias API bajo `backend/`. | `role-access.spec.js`, `approvals.spec.js`, otros recorridos Playwright y pruebas API de roles. |

La autorización no depende solo de ocultar botones: los routers usan un principal autenticado y comprueban roles, propiedad de reserva o asignación de espacio. Por ejemplo, las bandejas de aprobación devuelven solo espacios asignados y el backend rechaza una decisión de un rol no autorizado. La prueba E2E de acceso directo comprueba ventanas sin sesión; no existe una ruta de cliente independiente para cada página ni una prueba de deep links autenticados, porque la aplicación no usa React Router.

## 2.8. Cambio de la regla de cuatro horas

### Regla anterior y cambio aprobado

La propuesta inicial de OpenSpec declara expresamente que no habría un máximo independiente de duración por reserva; el plan dejaba la duración máxima pendiente de definición. El cambio `enforce-four-hour-reservation-limit` justifica que el comportamiento anterior permitía reservas más largas y agrega un límite de cuatro horas consecutivas por usuario y espacio. Por ello, no se trata de una regla inicial del plan, sino de una decisión posterior documentada y aplicada.

Más adelante, `arbitrary-start-reservation-durations` cambió la alineación: antes el backend exigía inicio y fin en `:00` o `:30`; ahora permite un inicio a cualquier minuto exacto y conserva duraciones en múltiplos de 30. Este cambio no quitó ni aumentó el máximo individual de cuatro horas ni el acumulado.

### Cálculo actual

El validador de `backend/politicas/validation.py` exige una duración individual de 30, 60, 90 y así sucesivamente hasta 240 minutos. El inicio puede ser, por ejemplo, 10:17; si se elige media hora, el fin es 10:47. Se rechazan segundos/microsegundos, duraciones de 45 minutos, cruces de día, domingos, horas fuera del horario y solicitudes fuera del plazo de anticipación.

El cálculo consecutivo de `backend/politicas/consecutive.py` considera únicamente reservas `pending` y `approved` del mismo usuario y espacio, normalizadas a UTC. Ordena los intervalos y los une si el fin de uno coincide exactamente con el inicio del siguiente. Una pausa inicia otra secuencia. Se permite una secuencia de exactamente cuatro horas; si la operación que se evalúa hace que la secuencia pase de cuatro horas, se rechaza. Reservas de otro espacio se evalúan por separado.

Al modificar una reserva, el servicio excluye el intervalo viejo y evalúa el propuesto como reemplazo; no cuenta ambos intervalos a la vez. En un cambio sujeto a aprobación, la reserva original queda vigente y el intervalo propuesto se bloquea provisionalmente para disponibilidad; al aprobar, el servicio vuelve a comprobar el límite dentro de la transacción. Si la aprobación ya no cumple la regla, no sustituye la reserva original. Al rechazar, libera la propuesta. Las reservas antiguas que excedan el límite se conservan hasta que se intente un cambio incompatible; no hay ajuste automático.

La comprobación de cruce entre reservas o mantenimientos usa intervalos semiabiertos: `inicioA < finB` y `inicioB < finA`. Dos reservas contiguas no son conflicto de disponibilidad, pero sí pertenecen a la misma secuencia para el límite acumulado. La lectura de reservas activas, validación y escritura se hace dentro de la transacción de SQLite para reducir carreras entre operaciones concurrentes.

### Archivos y pruebas relacionados

El commit `92cc23b` (23 de octubre de 2026) incorpora el validador acumulado, los servicios de reserva y aprobación, pruebas y el cambio OpenSpec. El cambio posterior `3c1d251` (24 de octubre de 2026) incorpora inicios libres con duraciones de 30 minutos. Los archivos clave son:

- `backend/politicas/validation.py` y `backend/politicas/consecutive.py`.
- `backend/reservas/service.py` y `backend/aprobaciones/service.py`.
- `backend/tests/test_policies.py` y `backend/tests/test_reservations.py`.
- `frontend/src/AvailabilityPage.jsx`, `frontend/src/ReservationsPage.jsx` y `frontend/src/reservationTime.js`.
- `frontend/tests/e2e/availability.spec.js` y `frontend/tests/e2e/reservations.spec.js`.
- `openspec/changes/enforce-four-hour-reservation-limit/` y `openspec/changes/arbitrary-start-reservation-durations/`.

Las pruebas incluyen exactamente cuatro horas válidas, una reserva individual excesiva, acumulación de reservas contiguas, reinicio después de pausa, espacios separados, concurrencia, sustitución de intervalos y revalidación al aprobar. Playwright también prueba el rechazo por límite acumulado y el flujo de inicio 10:17 más 30 minutos igual a 10:47. La ejecución completa de pytest y Playwright pasó, como se detalla en la sección siguiente.

## 2.9. Pruebas y resultados reales

### Herramientas y aislamiento

El backend usa pytest y HTTPX/FastAPI TestClient; los fixtures guardan sus SQLite bajo directorios temporales de pytest. El archivo `frontend/playwright.config.js` ejecuta Playwright con un solo worker, inicia Vite y FastAPI en puertos 5173 y 8000 y crea una base SQLite temporal con datos E2E. La suite no necesita usar la base local `.local/`.

Se ejecutaron las pruebas el 24 de octubre de 2026 desde el repositorio actual. Versiones observadas: Python 3.12.2, pytest 8.4.2, HTTPX 0.28.1, Node 22.14.0, npm 10.9.2 y Playwright 1.64.1. La configuración Playwright usa el canal Google Chrome. No se generó ni calculó un porcentaje de cobertura.

### Comandos y resultados

| Grupo de pruebas | Qué verifica | Comando ejecutado | Resultado real | Observaciones |
|---|---|---|---|---|
| Backend: migraciones/aplicación | Creación de SQLite, aplicación idempotente de migraciones y compatibilidad con datos previos. | `.\.venv\Scripts\python.exe -m pytest` desde la raíz | 4/4 pasaron (`test_app.py`). | Usa bases temporales. |
| Backend: disponibilidad | Disponibilidad, reservas y mantenimientos coincidentes, límites contiguos, estados liberados y acceso autenticado. | Mismo comando pytest | 12/12 pasaron (`test_availability.py`). | Prueba API con datos aislados. |
| Backend: historial | Registro, filtros, alcance de roles, conservación y solo lectura. | Mismo comando pytest | 4/4 pasaron (`test_history.py`). | — |
| Backend: integración | Recorrido de cuenta, espacio, reserva, aprobación, cancelación e historial. | Mismo comando pytest | 1/1 pasó (`test_integration_workflow.py`). | Un escenario integrado; no equivale a una prueba desplegada en producción. |
| Backend: políticas | Calendario, anticipación, zona horaria, precisión de minuto y duración individual/acumulada. | Mismo comando pytest | 21/21 casos pasaron (`test_policies.py`). | Incluye parámetros de prueba. |
| Backend: reservas/aprobaciones | CRUD y estados, permisos, cancelación, aprobación/rechazo, vencimiento, cambios, concurrencia y regla de cuatro horas. | Mismo comando pytest | 47/47 casos pasaron (`test_reservations.py`). | Incluye escenarios parametrizados y transacciones concurrentes. |
| Backend: espacios/mantenimiento | Permisos, cambios de espacios, configuración de aprobación y conflictos de bloqueos. | Mismo comando pytest | 30/30 casos pasaron (`test_spaces.py`). | Incluye escenarios parametrizados. |
| Backend: usuarios/permisos | Alta inicial, contraseñas, edición, activación, roles, asignación y denegación. | Mismo comando pytest | 15/15 casos pasaron (`test_users.py`). | Incluye escenarios parametrizados. |
| **Backend completo** | Los ocho archivos anteriores. | `.\.venv\Scripts\python.exe -m pytest` | **134 pasaron, 0 fallaron, 0 omitidos.** | Duración observada: 42,78 s. Hubo 8 advertencias Starlette sobre `HTTP_422_UNPROCESSABLE_ENTITY` obsoleto. |
| Frontend E2E: autenticación | Inicio/cierre de sesión, cuentas inactivas, error de red, sesión vencida y paneles por rol. | `npm.cmd run test:e2e` desde `frontend` | 6/6 pasaron (`authentication.spec.js`). | Servidores y SQLite temporales iniciados por Playwright. |
| Frontend E2E: permisos/ventanas | Menús por rol, respuestas permitidas/403 de API y carga de URL directa sin sesión. | Mismo comando Playwright | 2/2 pasaron (`role-access.spec.js`). | La app no tiene rutas de cliente independientes. |
| Frontend E2E: disponibilidad/reservas | Estados, errores del backend, solicitar, consultar, modificar, cancelar y exceso acumulado de cuatro horas. | Mismo comando Playwright | 4/4 pasaron (`availability.spec.js`, `reservations.spec.js`). | Usa API real de la instancia E2E, no mocks de operaciones. |
| Frontend E2E: aprobaciones | Bandejas asignadas, motivo de rechazo, acceso denegado y aprobación de cambios. | Mismo comando Playwright | 3/3 pasaron (`approvals.spec.js`). | — |
| Frontend E2E: espacios/usuarios/historial | Administración y lectura de los módulos por rol. | Mismo comando Playwright | 7/7 pasaron (`spaces.spec.js`, `users.spec.js`, `history.spec.js`). | — |
| **Frontend E2E completo** | Los ocho archivos Playwright. | `npm.cmd run test:e2e` desde `frontend` | **22 pasaron, 0 fallaron, 0 omitidos.** | Duración observada: 21,6 s. Node mostró avisos de entorno `NO_COLOR`/`FORCE_COLOR`, sin fallo. |
| Build de frontend | Transformación y empaquetado de React con Vite. | `npm.cmd run build` desde `frontend` | **Correcto**, 37 módulos transformados. | Se ejecutó en aproximadamente 0,68 s; no es una prueba funcional del sitio desplegado. |
| OpenSpec cambios | Estructura y consistencia estricta de los cuatro cambios. | `openspec.cmd validate --changes --strict` desde la raíz | **4 pasaron, 0 fallaron.** | `openspec validate --specs --strict` informó que no hay capacidades canónicas en `openspec/specs/`. |

La prueba automatizada de rutas directas se limita a abrir ventanas sin sesión. Los permisos autenticados se prueban en los menús y en los endpoints. No hay una suite separada de pruebas unitarias de componentes React: las pruebas de interfaz existentes son E2E con Playwright.

### Resultados fallidos anteriores y correcciones

En una ejecución inicial durante el trabajo de pruebas, pytest obtuvo 133 aprobadas y 1 fallida: una prueba de decisión de cambio usaba fechas a 28 y 29 días, que podían caer fuera de la ventana de anticipación según el día actual. Se movieron los datos de prueba a 21 y 22 días; la ejecución completa actual pasa.

La primera ejecución de Playwright obtuvo 19 aprobadas y 1 fallida porque el conteo inicial de tarjetas se hacía antes de que terminara de cargar la lista de reservas. La prueba ahora espera a que aparezca el contador. También se difirió la eliminación del directorio SQLite E2E hasta terminar el proceso, evitando que la tarea periódica de vencimiento del backend acceda a la base mientras se cierra. La suite actual completa pasa. Estas correcciones aparecen en `3cc079d`.

## 2.10. Dificultades encontradas y decisiones modificadas

| Situación respaldada | Impacto | Decisión y estado |
|---|---|---|
| La propuesta del frontend registró que React solo tenía una pantalla inicial, aunque el backend ya tenía flujos funcionales. | Las personas no podían usar esos flujos desde la interfaz. | Se definieron siete capacidades de UI y luego se añadieron páginas React conectadas a la API. Los recorridos Playwright actuales comprueban los módulos. |
| La propuesta de interfaz encontró que la especificación de usuarios permitía editar datos, pero la API carecía de esa operación. | No era posible completar la administración de cuentas conforme a la especificación. | Se agregó la actualización de datos de cuenta en backend, junto con validación, historial y pantalla; hay pruebas pytest y Playwright. |
| La política inicial no establecía un máximo independiente de duración; la propuesta inicial de OpenSpec lo explicita. | La regla de uso equitativo requería una decisión posterior. | El cambio `enforce-four-hour-reservation-limit` introdujo cuatro horas individuales y consecutivas. Se reflejó en servicio, aprobación, UI y pruebas. |
| Backend y control inicial de horarios exigían alineación del reloj, pese a que la experiencia de selección necesitaba horas libres. | El usuario no podía usar, por ejemplo, una hora de inicio 10:17 con una duración regular. | `arbitrary-start-reservation-durations` permitió inicio a cualquier minuto, calculó el fin por duración y conservó los incrementos de 30 minutos; se probaron 10:17–10:47 y el rechazo de 45 minutos. |
| La prueba de cambio de reserva podía depender del calendario y la prueba E2E podía contar antes de terminar una carga asíncrona. | Fallos de pruebas no deterministas, no fallos de la lógica de negocio. | Se cambiaron fechas de fixture y se agregó espera por el indicador de carga; ahora pasan las suites completas. |
| El usuario reportó haber ejecutado `backend.bootstrap_admin`, módulo que no existe. | El comando de arranque inicial fallaba al resolver el módulo. | El punto de entrada real es `backend.usuarios.bootstrap_admin`; el README documenta ese comando. |
| La política de ejecución de PowerShell bloqueó el wrapper global `openspec.ps1`. | No se pudo ejecutar OpenSpec por ese wrapper. | Se usó el wrapper `openspec.cmd` instalado, sin modificar la política de PowerShell, y `validate --changes --strict` pasó los cuatro cambios. |

No se encontraron registros verificables de pruebas de carga de la aplicación desplegada, recuperación de respaldos, accesibilidad automatizada o evaluación de seguridad previa a producción. El plan identifica algunos de esos asuntos como estrategia o riesgo, pero eso no comprueba que se hayan ejecutado.

## 2.11. Ventajas y limitaciones de SDD, OpenSpec y Codex

### SDD

**Ventajas observables o razonables:** permite expresar reglas antes de implementarlas, derivar casos de prueba negativos y mantener trazabilidad entre requisitos y comportamiento. En este proyecto el cambio de cuatro horas y el de inicios arbitrarios tienen escenarios y pruebas relacionados.

**Limitaciones:** crear y mantener especificaciones y trazabilidad requiere tiempo. Si no se sincronizan o archivan, pueden coexistir requisitos en cambios activos sin una referencia canónica; eso ocurre en el estado actual de `openspec/specs/`. No hay mediciones para afirmar cuánto redujo defectos o retrabajo.

### OpenSpec

**Ventajas observables:** separa motivación (`proposal.md`), decisiones técnicas (`design.md`), requisitos de comportamiento y escenarios (`specs/`) y trabajo verificable (`tasks.md`). Los cuatro cambios actuales superan la validación estructural estricta.

**Limitaciones observadas:** todos los cambios permanecen en `openspec/changes/`; el directorio canónico `openspec/specs/` no contiene capacidades. La lista de tareas marcada completa y una validación estructural no son equivalentes a una revisión humana de cada escenario ni prueban automáticamente el código. No se encontró evidencia de un flujo formal de archivo/sincronización ya completado.

### Codex

**Utilidad en el proceso:** la conversación de trabajo documenta asistencia solicitada para implementar pantallas, corregir flujos, añadir pruebas y documentar el proyecto. Un agente puede ayudar a recorrer archivos y ejecutar comandos con rapidez.

**Riesgos y controles:** una respuesta puede equivocarse, asumir detalles o producir pruebas frágiles. La prueba de calendario y la espera de carga asíncrona muestran por qué se deben ejecutar las suites y corregir lo que revelan. No hay bitácora de prompts ni medición de ahorro de tiempo, por lo que esas cifras no se reportan. La responsabilidad de aceptar reglas y cambios sigue siendo humana, como establece el plan.

Estas observaciones sobre ventajas generales no deben confundirse con métricas demostradas en el repositorio.

## 2.12. Estado actual y trabajo pendiente

### Estado comprobado

- Backend, frontend y módulos principales están presentes y conectados.
- Los roles implementados son solicitante, aprobador y administrador; la API aplica permisos además de la navegación por rol.
- Las 134 pruebas pytest y 22 pruebas E2E pasaron en la ejecución de este informe; el build Vite también pasó.
- Los cuatro cambios OpenSpec superaron `validate --changes --strict` y sus tareas están marcadas completas.
- `PLAN_INGENIERIA.md` se leyó y no fue modificado.

### Trabajo recomendado antes de cerrar el proyecto

1. Sincronizar o archivar las capacidades de cambios completados en `openspec/specs/`, si el proceso del curso/equipo lo requiere, y repetir validación.
2. Revisar y completar la lista de cierre que sigue sin marcar en `PLAN_INGENIERIA.md`; este informe no la cambia ni certifica la revisión humana.
3. Definir cómo crear cuentas y gestionar datos iniciales en un despliegue compartido, así como copias de seguridad y recuperación de SQLite.
4. Evaluar despliegue seguro (TLS, secretos, configuración, monitoreo y permisos del archivo de base de datos) antes de manejar datos institucionales reales. No se comprobó un despliegue productivo.
5. Decidir si se necesita navegación mediante enlaces profundos; hoy las ventanas son estado interno de React y la ruta directa no identifica una vista autenticada.
6. Considerar pruebas unitarias de componentes, accesibilidad, rendimiento y compatibilidad con navegadores adicionales si son criterios de entrega. No se encontraron esas suites.
7. Revisar las ocho advertencias de obsolescencia de Starlette cuando se actualice FastAPI/Starlette; no provocaron fallos en esta ejecución.
8. Probar instalación y arranque desde un clon limpio. Las pruebas de este informe se ejecutaron en el checkout existente, con sus dependencias ya instaladas; no se ejecutó `git clone` ni `npm ci` en un entorno nuevo. Además, las dependencias Python se especifican con rangos y no cuentan con un lockfile.

No se marca como pendiente la implementación de reportes, auditoría, correo u otras funciones fuera de alcance; se indican como limitaciones de esta versión y deben priorizarse explícitamente si se requieren.

## 2.13. Conclusiones

La planificación inicial identificó el problema, actores, arquitectura, módulos, riesgos y tipos de prueba. Esa base se refleja en la estructura modular y en las etapas visibles en el historial de Git. La persistencia en SQLite, la separación del frontend/backend y las pruebas contra datos aislados hacen que una instalación local sea reproducible, aunque el entorno de producción no se ha definido.

SDD y OpenSpec dieron un lugar para expresar cambios de comportamiento y convertirlos en tareas y escenarios; el historial registra que las reglas de cuatro horas e inicios flexibles se trataron como cambios explícitos. La validación OpenSpec confirma que los cuatro paquetes de cambio cumplen su estructura estricta, pero no hay especificaciones canónicas publicadas en `openspec/specs/` y el checklist global del plan no está cerrado.

Codex fue utilizado como apoyo en la conversación de desarrollo para código, pruebas y documentación. La revisión humana fue necesaria para detectar necesidades visibles durante el uso y para orientar los cambios; el repositorio no contiene una bitácora suficiente para atribuir autoría de cada cambio o certificar aprobación formal de todo el código.

La ejecución actual ofrece evidencia favorable pero acotada: 134 pruebas backend, 22 recorridos E2E, compilación de frontend y validación estricta de los cuatro cambios OpenSpec pasaron. Esto verifica muchos flujos funcionales y permisos en un entorno local aislado; no demuestra ausencia total de errores, seguridad productiva, rendimiento a escala ni recuperación ante pérdida de datos.

Antes de considerar el proyecto cerrado, conviene sincronizar el estado canónico de OpenSpec, completar la revisión de cierre del plan, documentar el despliegue y respaldo, y acordar si las limitaciones enumeradas son aceptables para la evaluación o deben convertirse en nuevos requisitos.

## 2.14. Referencias técnicas

Documentación oficial consultada para contextualizar las herramientas y tecnologías; la implementación del proyecto se contrastó además con los archivos y pruebas citados en las secciones anteriores.

- OpenSpec, [Quickstart y flujo de cambios](https://openspec.dev/docs/quickstart), [configuración del proyecto](https://openspec.dev/docs/configuration) y [CLI](https://openspec.dev/docs/cli).
- FastAPI, [Tutorial oficial](https://fastapi.tiangolo.com/tutorial/).
- React, [Quick Start](https://react.dev/learn).
- Vite, [Getting Started](https://vite.dev/guide/).
- Python, [módulo `sqlite3`](https://docs.python.org/3/library/sqlite3.html).
- SQLite, [Transactions](https://www.sqlite.org/lang_transaction.html).
- pytest, [Getting Started](https://pytest.org/en/latest/getting-started.html).
- Playwright, [Writing tests](https://playwright.dev/docs/writing-tests).

## Fuentes del repositorio revisadas

- Plan y documentación: `PLAN_INGENIERIA.md`, `README.md`, `TRAZABILIDAD_REQUISITOS_PRUEBAS.md`, `.gitignore`, `requirements.txt`, `requirements-dev.txt` y `frontend/package.json` / `package-lock.json`.
- OpenSpec: `openspec/config.yaml` y los cuatro directorios bajo `openspec/changes/`, incluidos propuestas, diseños, especificaciones y tareas; también se comprobó `openspec/specs/`.
- Backend: `backend/main.py`, `database.py`, migraciones, módulos de usuarios, espacios, políticas, disponibilidad, reservas, aprobaciones e historial.
- Frontend: `frontend/src/`, `vite.config.js`, `playwright.config.js` y `frontend/tests/e2e/`.
- Pruebas: ocho archivos `backend/tests/test_*.py` y ocho archivos `frontend/tests/e2e/*.spec.js`.
- Historial de Git: commits del 23 y 24 de octubre de 2026 consultados para establecer el orden de las etapas y cambios.
