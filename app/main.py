from fastapi import FastAPI, HTTPException

from app.orchestrator import Orchestrator
from app.planner import PlannerError, QwenPlanner
from app.schemas import AgentRequest, AgentResponse


app = FastAPI(title="Mini Agent Orchestrator", version="1.0.0")
planner = QwenPlanner()
orchestrator = Orchestrator()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/agent/request", response_model=AgentResponse)
async def process_request(payload: AgentRequest) -> AgentResponse:
    try:
        plan = await planner.create_plan(payload.query)
    except PlannerError as exc:
        raise HTTPException(status_code=400, detail=f"Planner failed: {exc}") from exc

    return await orchestrator.run(plan)
