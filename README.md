# Sistema de reservas académicas

Aplicación web para gestionar la reserva de espacios académicos universitarios. Reúne en una interfaz las consultas de disponibilidad y las solicitudes de reserva, mientras el backend aplica permisos, políticas horarias y prevención de conflictos. Está dirigida a solicitantes, aprobadores y administradores de espacios.

## Funcionalidades implementadas

- **Autenticación y acceso por rol:** inicio y cierre de sesión con cuentas institucionales. El backend protege los endpoints y la interfaz muestra las opciones correspondientes al rol autenticado.
- **Espacios:** consulta de espacios y, para administradores, creación, edición, activación/desactivación, configuración de aprobación y gestión de bloqueos por mantenimiento.
- **Usuarios:** el administrador puede crear cuentas inactivas, editar sus datos, activar/desactivar cuentas, cambiar los roles permitidos y asignar o retirar aprobadores de espacios.
- **Disponibilidad:** consulta por espacio e intervalo. El servicio informa si el intervalo está disponible, ocupado o bloqueado por mantenimiento.
- **Reservas:** un solicitante puede crear solicitudes, consultar sus reservas, proponer cambios y cancelar según estado y plazo. Los intervalos nuevos se vuelven a validar en el servidor.
- **Aprobaciones:** cada aprobador consulta y decide solicitudes y cambios de los espacios que tiene asignados. Rechazar exige motivo; un aprobador no puede aprobar su propia solicitud.
- **Historial:** consulta de eventos según el alcance del rol, con filtros por entidad.
- **Políticas y conflictos:** el backend valida horario, anticipación, estado del espacio, reservas y mantenimientos que se cruzan. El inicio puede elegirse con precisión de minuto; la duración debe ser múltiplo de 30 minutos entre 30 minutos y cuatro horas. Además, una secuencia de reservas pendientes y aprobadas que se toquen del mismo usuario y espacio no puede superar cuatro horas acumuladas.
- **Vencimiento:** una solicitud que sigue pendiente al llegar su hora de inicio vence automáticamente y libera el intervalo.

Las tareas de interfaz, integración y cambios de horarios en los archivos `tasks.md` inspeccionados bajo `openspec/changes/` están marcadas como completadas. Las reglas de negocio se validan en el backend; las validaciones visuales del frontend no reemplazan esas comprobaciones.

## Tecnologías

| Área | Tecnología detectada |
|---|---|
| Backend y API | Python, FastAPI (`fastapi>=0.115,<1`) y Uvicorn (`uvicorn>=0.30,<1`) |
| Base de datos | SQLite, mediante el módulo `sqlite3` de Python; no requiere un servidor separado |
| Migraciones | Archivos SQL versionados ejecutados automáticamente al iniciar la API |
| Frontend | React y React DOM 19.3.1; Vite 6.4.5 (versiones resueltas en `package-lock.json`) |
| Desarrollo frontend | Node.js y npm; plugin React para Vite 4.7.0 (versión del lockfile) |
| Pruebas backend | pytest (`>=8,<9`) y HTTPX (`>=0.27,<1`); ver las versiones probadas abajo |
| Pruebas de interfaz | Playwright 1.64.1 (lockfile), Chromium usando el canal Google Chrome |
| Zona horaria | `America/Bogota`; `tzdata` se declara para sistemas que no incluyen la base IANA |

Las dependencias de producción del backend están en `requirements.txt`, las de desarrollo y pruebas en `requirements-dev.txt`, y las del frontend en `frontend/package-lock.json` y `frontend/package.json`. Las versiones Python están declaradas como rangos, no están fijadas en un lockfile. En el entorno donde se comprobó esta guía estaban instalados FastAPI 0.162.0, Uvicorn 0.54.0, pytest 8.4.2, HTTPX 0.28.1 y tzdata 2026.5; una instalación posterior puede resolver otras versiones dentro de los rangos.

## Requisitos previos

- Git.
- Python **3.10 o posterior** (el código usa sintaxis de Python 3.10; se verificó con Python 3.12.2).
- Node.js **18 o posterior** y npm (el proyecto se verificó con Node 22.14.0 y npm 10.9.2).
- Google Chrome para ejecutar Playwright, salvo que ya esté instalado. No es necesario para desarrollar o abrir el frontend.
- Un navegador web moderno para utilizar la aplicación.

No se necesita instalar SQLite por separado: Python incluye el módulo que usa el backend. La disponibilidad de `tzdata` también se gestiona mediante las dependencias Python.

## Instalación desde cero

### 1. Clonar el repositorio

Sustituye `<URL_DEL_REPOSITORIO>` por la URL real del repositorio:

```sh
git clone <URL_DEL_REPOSITORIO>
cd actividad-ssd
```

### 2. Crear el entorno Python e instalar dependencias

En Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

En Linux o macOS:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

La activación del entorno virtual es opcional si se invoca directamente el ejecutable dentro de `.venv`. En PowerShell, para activarlo en la sesión actual:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si la política local de PowerShell impide la activación, usa los comandos con `.venv\Scripts\python.exe` mostrados aquí, sin cambiar la política de ejecución.

### 3. Instalar dependencias del frontend

Desde la carpeta `frontend`:

```sh
npm ci
```

En Windows PowerShell se puede usar `npm.cmd ci` si PowerShell no resuelve `npm`:

```powershell
npm.cmd ci
```

### 4. Configurar la base de datos

No hay un archivo `.env` obligatorio. En el primer inicio, la API crea el directorio `.local/`, la base `.local/academic_reservations.sqlite3` y aplica las migraciones SQL pendientes. Ambos están excluidos de Git.

Opcionalmente, se puede elegir otra ruta definiendo `ACADEMIC_RESERVATIONS_DB_PATH` antes de iniciar el backend. La ruta debe ser escribible por el usuario que ejecuta el proceso.

PowerShell:

```powershell
$env:ACADEMIC_RESERVATIONS_DB_PATH = ".local\reservas-desarrollo.sqlite3"
```

Linux o macOS:

```sh
export ACADEMIC_RESERVATIONS_DB_PATH=".local/reservas-desarrollo.sqlite3"
```

La configuración es una ruta a un archivo SQLite, no una URL de conexión. Para volver al valor predeterminado, elimina esa variable de la terminal (`Remove-Item Env:ACADEMIC_RESERVATIONS_DB_PATH` en PowerShell o `unset ACADEMIC_RESERVATIONS_DB_PATH` en POSIX). No se necesita ejecutar migraciones manualmente: `backend.main` las aplica al arrancar.

### 5. Crear el primer administrador

La aplicación no genera una cuenta administrativa predeterminada. Con el entorno virtual instalado, ejecuta desde la raíz del repositorio:

```powershell
.\.venv\Scripts\python.exe -m backend.usuarios.bootstrap_admin
```

En Linux o macOS, con el entorno activado:

```sh
python -m backend.usuarios.bootstrap_admin
```

El comando solicita nombre, correo institucional `@universidad.edu.co` y contraseña (mínimo 12 caracteres). La contraseña se solicita de forma interactiva y no debe escribirse en el README ni en comandos guardados. El inicializador solo crea el primer administrador; no crea usuarios de demostración. Después, el administrador puede crear las demás cuentas desde la interfaz. Las cuentas nuevas quedan inactivas hasta que se activen.

## Variables de entorno

| Variable | Uso | Valor predeterminado |
|---|---|---|
| `ACADEMIC_RESERVATIONS_DB_PATH` | Ruta del archivo SQLite del backend | `<raíz>/.local/academic_reservations.sqlite3` |
| `VITE_API_BASE_URL` | Base URL usada por el cliente HTTP del frontend | `/api` |
| `PYTHON_EXECUTABLE` | Opcional; ejecutable Python que Playwright usa para preparar su base E2E | `.venv` del repositorio si existe; si no, `py -3` en Windows o `python3` en Linux/macOS |

En desarrollo, Vite reenvía `/api` al backend en `http://127.0.0.1:8000` y retira el prefijo `/api`. Para utilizar otra ubicación del backend, `VITE_API_BASE_URL` puede apuntar directamente a la URL de la API; la configuración de proxy de Vite en `frontend/vite.config.js` también determina el destino cuando se usa `/api`.

No se incluye `.env.example` porque la configuración local solo requiere una ruta opcional de SQLite y los valores predeterminados funcionan sin archivo `.env`. `.env` está ignorado por Git; no guardes secretos en variables o archivos versionados.

## Ejecutar el sistema

Inicia los servicios en **dos terminales**, desde la raíz clonada.

### Terminal 1: backend

PowerShell:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Linux o macOS, con el entorno activado:

```sh
python -m uvicorn backend.main:app --reload
```

La API queda en `http://127.0.0.1:8000`. Comprueba `http://127.0.0.1:8000/health`; debe responder `{"status":"ok"}`. La documentación OpenAPI interactiva está en `http://127.0.0.1:8000/docs`.

### Terminal 2: frontend

```sh
cd frontend
npm run dev
```

En PowerShell, si es necesario:

```powershell
Set-Location frontend
npm.cmd run dev
```

Abre la URL que Vite muestre en la terminal; por defecto es `http://localhost:5173`. El cliente usa el proxy `/api` para comunicarse con FastAPI. Inicia sesión con la cuenta institucional creada en el paso de inicialización. La sesión del frontend se conserva solo mientras la página permanece abierta; al recargar se debe iniciar sesión de nuevo.

Para detener cualquiera de los servicios, vuelve a su terminal y pulsa `Ctrl+C`.

## Roles y uso

Los nombres internos de roles son `requester`, `approver` y `administrator`:

| Rol | Funciones disponibles en la aplicación |
|---|---|
| Solicitante (`requester`) | Consultar espacios y disponibilidad, solicitar reservas, consultar las propias y pedir cambios o cancelarlas sujeto a estado y plazo; consultar el historial dentro de su alcance. |
| Aprobador (`approver`) | Consultar espacios y disponibilidad, revisar y decidir solicitudes y cambios de los espacios asignados, y consultar el historial permitido para esos espacios. No puede decidir solicitudes propias. |
| Administrador (`administrator`) | Consultar espacios, disponibilidad e historial; administrar espacios, políticas de aprobación por espacio, bloqueos de mantenimiento, usuarios, roles permitidos y asignaciones de aprobadores. El backend protege las operaciones administrativas. |

Uso habitual:

1. Inicia sesión con tu cuenta institucional activa.
2. Abre **Consultar espacios** para revisar los espacios disponibles en el catálogo.
3. En **Consultar disponibilidad**, elige fecha, espacio, hora de inicio y duración. El servicio confirma el resultado; la interfaz solo permite continuar si informa disponibilidad.
4. Envía la solicitud. Según la configuración de aprobación del espacio, comienza pendiente o aprobada. Consulta su estado en **Mis reservas**.
5. Para un cambio, solicita el intervalo alternativo desde la reserva. Cuando el espacio requiere aprobación, se conserva la reserva original hasta que el aprobador decide; la propuesta también bloquea provisionalmente ese horario.
6. El aprobador abre **Solicitudes y cambios pendientes**, revisa el detalle y aprueba o rechaza; el rechazo requiere un motivo.
7. El administrador administra cuentas y espacios desde sus ventanas. Las cuentas creadas deben activarse antes de que su titular pueda iniciar sesión.

La interfaz y el backend muestran y aplican las políticas de horario, anticipación, disponibilidad, plazo de cancelación y duración acumulada. Los valores exactos están implementados en `backend/politicas/validation.py` y `backend/politicas/consecutive.py`; consulta la documentación OpenAPI para los campos actuales de cada endpoint.

## Pruebas y comprobaciones

### Backend (pytest)

Desde la raíz del repositorio, con las dependencias de `requirements-dev.txt` instaladas:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

En Linux o macOS, con el entorno activado:

```sh
python -m pytest
```

Las pruebas crean bases SQLite temporales o bajo el directorio temporal de pytest; no necesitan el servidor de desarrollo ni modifican la base local habitual.

### Pruebas E2E de frontend (Playwright)

Desde `frontend`, con `npm ci` completado y Google Chrome disponible:

```sh
npm run test:e2e
```

En PowerShell:

```powershell
npm.cmd run test:e2e
```

Si se necesita instalar el Chrome usado por la configuración de Playwright, desde `frontend` ejecuta:

```sh
npx playwright install chrome
```

En PowerShell se puede ejecutar `npx.cmd playwright install chrome`. E2E inicia por sí mismo FastAPI y Vite en los puertos `8000` y `5173`, prepara cuentas y datos de prueba en una base temporal y elimina esa base al finalizar. No inicies manualmente los servidores de desarrollo a la vez que esta suite. Si Python no está en `.venv`, puedes definir `PYTHON_EXECUTABLE` al ejecutar Playwright; por ejemplo, `PYTHON_EXECUTABLE=python3 npm run test:e2e` en POSIX o `$env:PYTHON_EXECUTABLE = "py"` en PowerShell (el fallback de Windows ya usa `py -3`).

### Build frontend

Desde `frontend`:

```sh
npm run build
```

En PowerShell, usa `npm.cmd run build`. El resultado se genera en `frontend/dist/`, ignorado por Git. El comando `npm run dev` sirve para desarrollo; para previsualizar un build local se puede ejecutar `npm run preview` después de compilar.

Las suites backend y E2E son distintas: pytest prueba servicios, API, permisos y reglas; Playwright prueba recorridos de interfaz contra una instancia aislada del backend. Ambas deben ejecutarse para revisar el comportamiento integrado.

## Estructura del proyecto

```text
.
├── backend/
│   ├── aprobaciones/       # Decisiones y bandejas de aprobación
│   ├── disponibilidad/    # Consultas de disponibilidad y conflictos
│   ├── espacios/          # Espacios y bloqueos de mantenimiento
│   ├── historial/         # Registro y consulta de auditoría
│   ├── migrations/        # Migraciones SQL versionadas
│   ├── politicas/         # Reglas temporales y duración consecutiva
│   ├── reservas/          # Ciclo y persistencia de reservas
│   ├── tests/             # Pruebas pytest
│   ├── usuarios/          # Cuentas, autenticación y permisos
│   ├── database.py        # Configuración SQLite
│   └── main.py            # Aplicación FastAPI
├── frontend/
│   ├── src/                # Aplicación React, páginas, estilos y cliente API
│   ├── tests/e2e/          # Recorridos Playwright
│   ├── package.json        # Scripts y dependencias
│   ├── package-lock.json   # Versiones instalables reproducibles de npm
│   └── vite.config.js      # Servidor de desarrollo y proxy API
├── openspec/               # Propuestas, diseño, especificaciones y tareas
├── requirements.txt        # Dependencias Python de ejecución
├── requirements-dev.txt    # Dependencias Python de desarrollo y pruebas
├── TRAZABILIDAD_REQUISITOS_PRUEBAS.md
└── PLAN_INGENIERIA.md      # Plan de ingeniería del proyecto
```

## Solución de problemas

- **No encuentra `python` o `pip`:** confirma que Python está instalado y usa el ejecutable del entorno (`.venv\Scripts\python.exe` en Windows o `python` tras activar `.venv` en Linux/macOS).
- **`No module named backend.bootstrap_admin`:** el módulo de inicialización real es `backend.usuarios.bootstrap_admin`; ejecuta el comando desde la raíz del repositorio.
- **El frontend no puede conectar con la API:** verifica que FastAPI responda en `http://127.0.0.1:8000/health`, que se inició desde la raíz y que Vite está usando su proxy `/api` configurado en `frontend/vite.config.js`.
- **Puerto 8000 o 5173 ocupado:** detén el proceso que lo usa o inicia el servidor en otro puerto. Si cambias el puerto del backend, actualiza también el destino del proxy de Vite o configura `VITE_API_BASE_URL` con la URL de API apropiada. Playwright tiene los puertos 8000 y 5173 configurados en `frontend/playwright.config.js`.
- **Error de permisos al escribir SQLite:** comprueba que el usuario tenga permisos de escritura sobre `.local/` o configura `ACADEMIC_RESERVATIONS_DB_PATH` con una ruta escribible.
- **Esquema SQLite desactualizado:** inicia la API desde el código actual; las migraciones pendientes se aplican automáticamente al comienzo. No edites `PRAGMA user_version` manualmente.
- **E2E no encuentra Chrome:** desde `frontend`, instala el navegador con `npx playwright install chrome` (o `npx.cmd` en PowerShell) y vuelve a ejecutar `npm run test:e2e`.
- **Playwright no encuentra Python:** crea `.venv` e instala `requirements-dev.txt`, o configura `PYTHON_EXECUTABLE` con un intérprete que tenga las dependencias Python del proyecto instaladas.
- **Instalación npm inconsistente:** desde `frontend`, ejecuta `npm ci` para instalar exactamente lo descrito por `package-lock.json`.
- **Inicio de sesión rechazado:** verifica que la cuenta exista, use correo institucional, esté activa y tenga el rol asignado. Las cuentas creadas por un administrador comienzan inactivas.

## Estado y limitaciones conocidas

- El primer administrador debe crearse manualmente; no hay credenciales predeterminadas ni usuarios demo para desarrollo.
- SQLite es el único motor configurado por el proyecto. No está documentada ni implementada aquí una base de datos de producción distinta.
- El token no persiste al recargar la página.
- La interfaz no integra notificaciones automáticas por correo ni el sistema de horarios/notas universitario; no hay reservas de equipos independientes ni control físico de puertas.
- La configuración de aprobación es por espacio; las políticas temporales del sistema están implementadas en backend, no como editor general de políticas en la interfaz.
- Las ventanas se gestionan mediante estado interno de la aplicación; no hay un router de cliente configurado para enlaces profundos de cada pantalla.
- Los requisitos mínimos son Python 3.10 y Node.js 18. En este entorno se verificaron Python 3.12.2, Node 22.14.0, npm 10.9.2, FastAPI 0.162.0, Uvicorn 0.54.0, pytest 8.4.2, HTTPX 0.28.1, tzdata 2026.5, React 19.3.1, Vite 6.4.5 y Playwright 1.64.1.
