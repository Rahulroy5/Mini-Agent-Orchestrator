import json
import os
import re
from typing import Any

import httpx

from app.schemas import Plan, PlanTask


class PlannerError(Exception):
    pass


class QwenPlanner:
    def __init__(self) -> None:
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "qwen3.5:2b")
        self.timeout_seconds = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "20"))

    async def create_plan(self, user_query: str) -> Plan:
        llm_plan = await self._create_plan_with_llm(user_query)
        if llm_plan is not None:
            return llm_plan

        fallback_plan = self._create_plan_fallback(user_query)
        if fallback_plan is None:
            raise PlannerError("Could not parse request into a valid plan")

        return fallback_plan

    async def _create_plan_with_llm(self, user_query: str) -> Plan | None:
        prompt = self._build_prompt(user_query)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a workflow planner. Return only valid JSON. "
                        "No markdown, no prose."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "format": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.ollama_host}/api/chat", json=payload)
                response.raise_for_status()
                raw = response.json()
        except Exception:
            return None

        content = raw.get("message", {}).get("content")
        if not content:
            return None

        parsed = self._extract_json(content)
        if parsed is None:
            return None

        try:
            return self._normalize_plan(parsed)
        except Exception:
            return None

    def _build_prompt(self, user_query: str) -> str:
        return (
            "Convert the user request into a workflow plan for these tools: "
            "cancel_order(order_id), send_email(email, message). "
            "Rules: If cancellation fails, email must not be sent. "
            "Return JSON using this schema exactly: "
            '{"tasks":[{"id":"1","action":"cancel_order","params":{"order_id":"..."},"depends_on":[]},'
            '{"id":"2","action":"send_email","params":{"email":"...","message":"..."},"depends_on":["1"]}]}. '
            "Only include the actions cancel_order and send_email. "
            f"User request: {user_query}"
        )

    def _extract_json(self, text: str) -> dict[str, Any] | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None

        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    def _normalize_plan(self, raw: dict[str, Any]) -> Plan:
        tasks = raw.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            raise PlannerError("Invalid plan format")

        normalized_tasks: list[PlanTask] = []
        for task in tasks:
            action = task.get("action")
            if action not in {"cancel_order", "send_email"}:
                continue

            normalized_tasks.append(
                PlanTask(
                    id=str(task.get("id", len(normalized_tasks) + 1)),
                    action=action,
                    params=task.get("params") or {},
                    depends_on=[str(dep) for dep in (task.get("depends_on") or [])],
                )
            )

        if not normalized_tasks:
            raise PlannerError("Plan does not contain supported tasks")

        return Plan(tasks=normalized_tasks)

    def _create_plan_fallback(self, user_query: str) -> Plan | None:
        order_match = re.search(r"(?:order\s*#?|#)(\d+)", user_query, re.IGNORECASE)
        email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", user_query)

        if not order_match or not email_match:
            return None

        order_id = order_match.group(1)
        email = email_match.group(0)

        return Plan(
            tasks=[
                PlanTask(
                    id="1",
                    action="cancel_order",
                    params={"order_id": order_id},
                    depends_on=[],
                ),
                PlanTask(
                    id="2",
                    action="send_email",
                    params={
                        "email": email,
                        "message": f"Your order #{order_id} has been cancelled.",
                    },
                    depends_on=["1"],
                ),
            ]
        )
