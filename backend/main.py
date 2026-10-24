"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from backend.database import initialize_database
from backend.espacios.router import router as spaces_router
from backend.reservas.router import router as reservations_router
from backend.usuarios.router import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.database_path = initialize_database()
    yield


app = FastAPI(
    title="Sistema de reservas académicas",
    lifespan=lifespan,
)
app.include_router(users_router)
app.include_router(spaces_router)
app.include_router(reservations_router)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}
