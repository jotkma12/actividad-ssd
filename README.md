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
