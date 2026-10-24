"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager, suppress
import logging
from typing import AsyncIterator

from fastapi import FastAPI

from backend.aprobaciones.router import router as approvals_router
from backend.database import initialize_database
from backend.disponibilidad.router import router as availability_router
from backend.espacios.router import router as spaces_router
from backend.reservas.router import router as reservations_router
from backend.reservas.states import expire_due_pending_reservations
from backend.usuarios.router import router as users_router


logger = logging.getLogger(__name__)
PENDING_EXPIRATION_INTERVAL_SECONDS = 1


async def _expire_pending_requests_periodically() -> None:
    while True:
        try:
            await asyncio.to_thread(expire_due_pending_reservations)
        except Exception:
            logger.exception("No fue posible vencer las solicitudes pendientes")
        await asyncio.sleep(PENDING_EXPIRATION_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.database_path = initialize_database()
    expiration_task = asyncio.create_task(_expire_pending_requests_periodically())
    try:
        yield
    finally:
        expiration_task.cancel()
        with suppress(asyncio.CancelledError):
            await expiration_task


app = FastAPI(
    title="Sistema de reservas académicas",
    lifespan=lifespan,
)
app.include_router(users_router)
app.include_router(spaces_router)
app.include_router(reservations_router)
app.include_router(availability_router)
app.include_router(approvals_router)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}
