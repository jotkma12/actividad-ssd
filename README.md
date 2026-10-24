# Sistema de reservas académicas

Aplicación inicial organizada como un backend FastAPI, una interfaz React y una base de datos SQLite local.

## Backend

En PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

La API responde en `http://127.0.0.1:8000/health` y su documentación interactiva está en `http://127.0.0.1:8000/docs`.

La base SQLite se crea al iniciar el servidor en `.local/academic_reservations.sqlite3` y recibe las migraciones versionadas pendientes desde `backend/migrations/versions/`. Se puede cambiar la ruta con la variable `ACADEMIC_RESERVATIONS_DB_PATH`. El archivo local está excluido de Git.

### Cuentas y permisos

La aplicación no crea administradores al iniciar. Para configurar explícitamente el primer administrador activo, ejecuta desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe -m backend.usuarios.bootstrap_admin
```

El comando solicita nombre completo, correo `@universidad.edu.co` y contraseña. Solo crea la cuenta si todavía no existe un administrador. Todas las contraseñas deben tener al menos 12 caracteres; no se exige una combinación concreta de letras, números o símbolos. Las cuentas ordinarias se crean por `POST /users` con una sesión de administrador y empiezan inactivas. Un administrador puede activarlas, desactivarlas, cambiar roles y asignar aprobadores a espacios. La API documentada en `/docs` ofrece `POST /auth/login` y las operaciones protegidas usan `Authorization: Bearer <token>`.

### Espacios académicos

`GET /spaces` y `GET /spaces/{id}` consultan espacios activos e inactivos. Solo un administrador puede crearlos (`POST /spaces`), editar sus datos (`PUT /spaces/{id}`), cambiar su estado (`PATCH /spaces/{id}/status`) o cambiar si requieren aprobación (`PATCH /spaces/{id}/approval-policy`, con `requires_approval`). Al desactivar un espacio, la respuesta indica cuántas reservas futuras pendientes o aprobadas debe revisar el administrador; no se cancelan automáticamente. Cada espacio requiere una configuración de aprobación al crearse; cambiarla se registra en el historial y no altera reservas existentes. Las solicitudes nuevas consultan la configuración vigente: comienzan pendientes si requieren aprobación y aprobadas en caso contrario.

Los bloqueos de mantenimiento se consultan en `GET /spaces/{id}/maintenance-blocks`; un administrador puede crearlos con `POST`, modificarlos con `PUT` y retirarlos con `DELETE` en esa misma ruta. Si el intervalo se cruza con una reserva pendiente o aprobada, la API rechaza la operación e identifica las reservas que deben resolverse; una modificación fallida conserva el bloqueo existente. Cuando resolver el conflicto requiere cancelar o cambiar una reserva, el administrador contacta manualmente al solicitante por un canal institucional, como una llamada o un mensaje. El sistema no envía correos automáticos ni integra servicios de notificación.

### Políticas de reserva

El validador compartido `backend.politicas.validation.validate_reservation_interval` interpreta horas sin zona como hora local de `America/Bogota`, valida bloques de 30 minutos, permite reservas de lunes a sábado entre las 07:00 y las 21:00 y exige entre 24 horas y 30 días de anticipación. Además, ninguna secuencia de reservas pendientes y aprobadas del mismo usuario y espacio puede superar cuatro horas: solo se acumulan intervalos que se tocan exactamente, una pausa reinicia el cómputo y los espacios se evalúan por separado. Se permiten exactamente cuatro horas. Las reservas existentes que ya superen el límite se conservan, pero se rechazan las modificaciones cuyo resultado lo incumpla. La cancelación por el solicitante de una reserva aprobada está permitida hasta dos horas antes del inicio.

### Ciclo de reservas

Las reservas usan los estados `pending`, `approved`, `rejected`, `rejected_expired`, `cancelled` y `finished`. `GET /reservations` y `GET /reservations/{id}` muestran los registros permitidos para el rol: el administrador consulta todos, el solicitante los propios y el aprobador los de espacios asignados. Al consultar, las reservas aprobadas cuyo fin ya pasó se marcan como finalizadas. Un solicitante activo crea una solicitud con `POST /reservations`, indicando espacio y horario; el sistema valida las políticas y la disponibilidad dentro de la misma transacción SQLite. Las solicitudes de espacios que requieren aprobación comienzan en `pending`; las demás comienzan en `approved`. Una solicitud aún pendiente al llegar su hora de inicio pasa automáticamente a `rejected_expired`, registra el motivo y libera el intervalo. `PUT /reservations/{id}` permite al solicitante cambiar su reserva pendiente o una aprobada dentro del plazo y sujeto a políticas y disponibilidad. Para un espacio que requiere aprobación, la reserva original conserva su estado y horario mientras se revisa el cambio, y el nuevo horario queda bloqueado provisionalmente. Al aprobar, el nuevo horario reemplaza al original; al rechazar, se conserva el original y se libera el propuesto. Se puede cancelar con `POST /reservations/{id}/cancel`: el solicitante cancela sus pendientes antes de resolverlas y las aprobadas hasta dos horas antes; el administrador puede cancelar pendientes o aprobadas indicando un motivo. El motivo del solicitante es opcional. Si se cancela la reserva original mientras su cambio está pendiente, también se cancela la solicitud de cambio.

### Aprobaciones

Un aprobador activo consulta `GET /approvals/pending` y recibe solo solicitudes pendientes de los espacios que tiene asignados. Para decidir, envía `POST /approvals/reservations/{id}/decision` con `{"decision":"approve"}` o `{"decision":"reject","reason":"..."}`. Solo el aprobador asignado puede decidir y no puede decidir una solicitud propia. El rechazo requiere motivo; la decisión actualiza el estado una sola vez dentro de una transacción SQLite y registra actor, acción y motivo en el historial. Las solicitudes pendientes vencen al llegar su hora de inicio y ya no admiten aprobación. Los cambios de reservas aprobadas se consultan en `GET /approvals/pending-changes` y se resuelven con `POST /approvals/change-requests/{id}/decision`; siguen las mismas restricciones de asignación y autoaprobación, y el rechazo requiere motivo.

### Historial

`GET /history` entrega eventos de auditoría en orden cronológico. Se puede filtrar con `entity_type` y `entity_id`. Un administrador puede consultar eventos de todas las entidades; un solicitante solo ve eventos de sus reservas; un aprobador ve eventos de reservas, espacios y mantenimientos dentro de los espacios que tiene asignados. Las operaciones de cuentas, roles y asignaciones, espacios, reservas, decisiones y mantenimientos registran actor, momento, acción, valores anteriores y nuevos y motivo cuando corresponde. El historial no tiene operaciones normales de edición o borrado.

### Disponibilidad

Una persona con sesión activa puede consultar `GET /availability/spaces/{id}` con `starts_at` y `ends_at`. La respuesta distingue `available`, `occupied` y `blocked`. Solo las reservas pendientes o aprobadas ocupan el intervalo; los bloqueos por mantenimiento también lo bloquean. Los cruces usan intervalos semiabiertos: si una reserva o bloqueo termina justo cuando comienza el intervalo consultado, no hay cruce. Los bloqueos nuevos o modificados se rechazan si coinciden con reservas pendientes o aprobadas y el bloqueo anterior se conserva ante un cambio conflictivo.

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Pruebas

Desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe -m pytest
```
