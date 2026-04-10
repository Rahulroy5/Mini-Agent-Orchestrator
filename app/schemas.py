from typing import Any, Literal

from pydantic import BaseModel, Field


TaskAction = Literal["cancel_order", "send_email"]


class AgentRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language user request")


class PlanTask(BaseModel):
    id: str
    action: TaskAction
    params: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    tasks: list[PlanTask]


class TaskResult(BaseModel):
    task_id: str
    action: TaskAction
    success: bool
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class AgentEvent(BaseModel):
    type: str
    detail: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    status: Literal["success", "failed"]
    message: str
    plan: Plan
    steps: list[TaskResult]
    events: list[AgentEvent]
