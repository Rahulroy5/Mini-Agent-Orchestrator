# mini-agent-orchestrator

Production-ready FastAPI service that connects to a local Ollama model and exposes simple health/status/chat APIs.

## Stack

- FastAPI
- Uvicorn
- HTTPX
- Pydantic + pydantic-settings
- Ollama (local LLM)
- uv (dependency and lock management)

## Project structure

- app/main.py
- app/api/routes.py
- app/core/config.py
- app/services/llm_service.py
- app/models/schemas.py
- tests/test_api.py
- start.sh
- pyproject.toml
- uv.lock

## Setup

1. Copy environment template:

```bash
cp .env.example .env
```

2. Install runtime deps:

```bash
uv sync
```

3. Install dev deps:

```bash
uv sync --extra dev
```

## Run

```bash
chmod +x start.sh
./start.sh
```

Server defaults to `http://0.0.0.0:8000`.

## API

### Health

```bash
curl http://127.0.0.1:8000/health
```

### LLM status

```bash
curl http://127.0.0.1:8000/llm-status
```

### Chat

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Explain async IO in one sentence."}'
```

## Tests

```bash
uv run pytest
```
