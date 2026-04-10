# Mini Agent Orchestrator

A lightweight, event-driven FastAPI agent that:
- plans tool actions from natural language using `qwen3.5:2b` via Ollama,
- executes async mock tools,
- enforces guardrails (no email if cancellation fails).

## Features

- Single API endpoint: `POST /agent/request`
- Planner:
  - Primary: local LLM call to Ollama `qwen3.5:2b`
  - Fallback: regex parser if LLM is unavailable
- Async tools:
  - `cancel_order(order_id)` with simulated 20% random failure
  - `send_email(email, message)` with 1-second async delay
- Event-driven orchestration with event log in response

## Setup

1. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Ensure Ollama is running with model:

```bash
ollama pull qwen3.5:2b
ollama run qwen3.5:2b
```

3. Optional environment config:

```bash
cp .env.example .env
```

4. Run API server:

```bash
uvicorn app.main:app --reload
```

## API Usage

Request:

```bash
curl -X POST "http://127.0.0.1:8000/agent/request" \
  -H "Content-Type: application/json" \
  -d '{"query":"Cancel my order #9921 and email me the confirmation at user@example.com."}'
```

Response includes:
- `status`: `success` or `failed`
- `message`: user-facing summary
- `plan`: generated tasks
- `steps`: execution results
- `events`: workflow event stream

## Failure Guardrail

If `cancel_order` fails, the orchestrator returns a failed state immediately and does not execute `send_email`.
