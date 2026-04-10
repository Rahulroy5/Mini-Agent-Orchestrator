from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.models.schemas import ChatRequest, ChatResponse, HealthResponse, LLMStatusResponse
from app.services.agent_service import run_agent_request
from app.services.llm_service import OllamaService


router = APIRouter()
STATIC_INDEX = Path(__file__).resolve().parents[1] / "static" / "index.html"


def get_llm_service(request: Request) -> OllamaService:
    return request.app.state.llm_service


@router.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(STATIC_INDEX)


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.get("/llm-status", response_model=LLMStatusResponse)
async def llm_status(
    llm_service: Annotated[OllamaService, Depends(get_llm_service)],
) -> LLMStatusResponse:
    settings = get_settings()
    is_ok = await llm_service.check_health()
    return LLMStatusResponse(
        status="ok" if is_ok else "unavailable",
        model=settings.model,
        ollama_url=settings.ollama_url,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    llm_service: Annotated[OllamaService, Depends(get_llm_service)],
) -> ChatResponse:
    settings = get_settings()

    try:
        workflow_status, plan, steps, thinking, reply = await run_agent_request(
            payload.message,
            llm_service,
            payload.system_prompt,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Request processing failed: {exc}") from exc

    return ChatResponse(
        model=settings.model,
        reply=reply,
        workflow_status=workflow_status,
        thinking=thinking,
        plan=plan,
        steps=steps,
    )
