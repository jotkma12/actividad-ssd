"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from backend.database import initialize_database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.database_path = initialize_database()
    yield


app = FastAPI(
    title="Sistema de reservas académicas",
    lifespan=lifespan,
)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Report that the API process is responding."""
    return {"status": "ok"}
