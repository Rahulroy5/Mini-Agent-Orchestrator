# Mini Agent Platform

Production-oriented local AI orchestration platform built with FastAPI and Ollama.

This repository contains two complementary services:

- A workflow orchestrator that converts user intent into executable tool steps (`/agent/request`).
- A chat + tool execution service with health checks, startup resilience, and a browser UI.

The project demonstrates practical agent patterns: planning, guardrails, retries, dependency-aware execution, and graceful degradation when the LLM is unavailable.

## Why This Project

Most "agent" demos stop at prompt-to-text output. This project goes further by modeling production concerns:

- Structured plan generation with deterministic fallback behavior.
- Tool dependency graph execution with early-fail guardrails.
- Local-first LLM integration (Ollama) with retry/backoff and startup checks.
- Observable workflows with explicit step traces and event logs.

## Architecture Overview

### 1) Root service: Mini Agent Orchestrator (`/app`)

- Endpoint: `POST /agent/request`
- Planner strategy:
  - Primary: LLM-generated structured plan from Ollama (`qwen3.5:2b`)
  - Fallback: regex-based parser when LLM output is unavailable/unparseable
- Executor strategy:
  - Runs tools asynchronously
  - Enforces dependency order
  - Stops downstream actions on failure
- Guardrail:
  - If cancellation fails, email is never sent

### 2) Subproject: Production FastAPI orchestrator (`/mini-agent-orchestrator`)

- Endpoints: `/health`, `/llm-status`, `/chat`
- Includes:
  - Typed schemas (Pydantic v2)
  - Ollama service abstraction (HTTPX + retry/backoff)
  - Startup health check hooks
  - Static frontend for interactive testing
  - Smart launcher script (`start.sh`) that:
    - validates Ollama availability
    - ensures model presence
    - finds an available port
    - avoids duplicate process launches

## Tech Stack

- Python 3.11+
- FastAPI + Uvicorn
- HTTPX
- Pydantic v2
- Ollama (`qwen3.5:2b`)
- pytest
- uv (in the subproject)

## Repository Structure

```text
Mini-agent/
  app/                          # Root orchestrator API
    main.py
    planner.py
    orchestrator.py
    tools.py
    schemas.py

  mini-agent-orchestrator/      # Production-style API + UI
    app/
      api/routes.py
      core/config.py
      services/
      static/
    tests/test_api.py
    start.sh
    pyproject.toml

  requirements.txt
  start.sh                      # Root convenience launcher
```

## Quick Start

### Prerequisites

- Python 3.11+
- Ollama installed and running
- Model available locally: `qwen3.5:2b`

```bash
ollama pull qwen3.5:2b
```

### Option A: Run the root orchestrator API

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload
```

API available at `http://127.0.0.1:8000`.

### Option B: Run the production-style subproject

From repository root, you can now launch directly:

```bash
bash start.sh
```

Or manually:

```bash
cd mini-agent-orchestrator
uv sync --extra dev
bash start.sh
```

## API Examples

### Root orchestrator

```bash
curl -X POST "http://127.0.0.1:8000/agent/request" \
  -H "Content-Type: application/json" \
  -d '{"query":"Cancel my order #9921 and email me at user@example.com"}'
```

### Subproject APIs

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/llm-status

curl -X POST "http://127.0.0.1:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message":"Explain async IO in one sentence."}'
```

## Testing

### Root project

```bash
pytest
```

### Subproject

```bash
cd mini-agent-orchestrator
uv run pytest
```

## Engineering Highlights

- Built a resilient planner-executor pipeline that combines LLM flexibility with deterministic fallback parsing.
- Implemented failure-aware orchestration where tool dependencies are explicitly modeled and enforced.
- Added service-level reliability patterns: retries with backoff, startup health verification, and safe shutdown.
- Designed responses for observability with plan traces, step-level outcomes, and workflow events.
- Structured codebase into clear boundaries: API, service layer, schemas, and tool adapters.

## Future Improvements

- Replace mock tools with real integrations (order management + transactional email provider).
- Add authentication, rate limiting, and request id tracing.
- Persist workflow events for analytics and replay.
- Add contract tests and CI pipeline checks.

## License

MIT (or your preferred license).
