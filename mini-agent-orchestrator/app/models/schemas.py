from pydantic import BaseModel, Field
from typing import Literal


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "mini-agent-orchestrator"


class LLMStatusResponse(BaseModel):
    status: str
    model: str
    ollama_url: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    system_prompt: str | None = Field(default=None, max_length=2000)


TaskAction = Literal["cancel_order", "send_email"]
StepStatus = Literal["success", "failed", "skipped"]


class PlanTask(BaseModel):
    id: str
    action: TaskAction
    params: dict[str, str] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)


class StepTrace(BaseModel):
    task_id: str
    action: TaskAction
    status: StepStatus
    detail: str


class ChatResponse(BaseModel):
    status: str = "ok"
    model: str
    reply: str
    workflow_status: Literal["success", "failed"] = "success"
    thinking: str = ""
    plan: list[PlanTask] = Field(default_factory=list)
    steps: list[StepTrace] = Field(default_factory=list)
