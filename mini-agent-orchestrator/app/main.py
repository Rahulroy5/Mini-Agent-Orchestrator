import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings
from app.services.llm_service import OllamaService


logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    llm_service = OllamaService(
        base_url=settings.ollama_url,
        model=settings.model,
        timeout_seconds=settings.ollama_timeout_seconds,
        retries=settings.ollama_retries,
        retry_backoff_seconds=settings.ollama_retry_backoff_seconds,
    )
    app.state.llm_service = llm_service

    if settings.ollama_startup_check:
        is_healthy = await llm_service.check_health()
        if is_healthy:
            logger.info("Ollama health check passed")
        else:
            logger.warning("Ollama health check failed at startup; app remains available")

    try:
        yield
    finally:
        await llm_service.aclose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="mini-agent-orchestrator",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
