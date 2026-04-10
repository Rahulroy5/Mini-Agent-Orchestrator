from fastapi.testclient import TestClient

from app.main import app


class MockLLMService:
    async def check_health(self) -> bool:
        return True

    async def chat(self, message: str, system_prompt: str | None = None) -> str:
        if system_prompt:
            return f"mocked:{system_prompt}:{message}"
        return f"mocked:{message}"


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        client.app.state.llm_service = MockLLMService()
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "mini-agent-orchestrator"


def test_chat_endpoint_with_mock_llm() -> None:
    with TestClient(app) as client:
        client.app.state.llm_service = MockLLMService()
        response = client.post(
            "/chat",
            json={
                "message": "Hello",
                "system_prompt": "You are concise",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["reply"] == "mocked:You are concise:Hello"
    assert payload["workflow_status"] == "success"
    assert payload["thinking"]
    assert payload["plan"] == []
    assert payload["steps"] == []


def test_chat_endpoint_runs_tool_workflow(monkeypatch) -> None:
    monkeypatch.setattr("app.services.tools.random.random", lambda: 0.99)

    with TestClient(app) as client:
        client.app.state.llm_service = MockLLMService()
        response = client.post(
            "/chat",
            json={
                "message": "Cancel my order #1234 and email me at user@example.com",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_status"] == "success"
    assert len(payload["plan"]) == 2
    assert len(payload["steps"]) == 2
    assert payload["steps"][0]["action"] == "cancel_order"
    assert payload["steps"][1]["action"] == "send_email"
