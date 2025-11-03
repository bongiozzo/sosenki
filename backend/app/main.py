"""SOSenki FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.api.routes import miniapp, requests, admin_requests
from backend.app.config import settings
from backend.app.database import Base, engine
from backend.app.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle (startup and shutdown)."""
    # Startup: Initialize database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")
    yield
    # Shutdown: Cleanup if needed
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.api_title,
    description="Open-source Telegram Mini App for property management",
    version=settings.api_version,
    lifespan=lifespan,
)


# Include routers
app.include_router(miniapp.router)
app.include_router(requests.router)
app.include_router(admin_requests.router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.info("Health check called")
    return {"status": "ok"}


# TODO: Mount static frontend (when ready)
# app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
