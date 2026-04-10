import asyncio
from typing import Any

import httpx


class OllamaService:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float,
        retries: int,
        retry_backoff_seconds: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.retries = max(0, retries)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self._client = httpx.AsyncClient(timeout=timeout_seconds)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def check_health(self) -> bool:
        try:
            response = await self._request_with_retry("GET", "/api/tags")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def chat(self, message: str, system_prompt: str | None = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        response = await self._request_with_retry("POST", "/api/chat", json=payload)
        data = response.json()

        if isinstance(data, dict):
            message_content = data.get("message", {}).get("content")
            if isinstance(message_content, str) and message_content.strip():
                return message_content.strip()

            raw_response = data.get("response")
            if isinstance(raw_response, str) and raw_response.strip():
                return raw_response.strip()

        raise ValueError("LLM returned an unexpected response format")

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        last_error: Exception | None = None

        for attempt in range(self.retries + 1):
            try:
                response = await self._client.request(
                    method,
                    f"{self.base_url}{path}",
                    json=json,
                )
                response.raise_for_status()
                return response
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_error = exc
                if attempt >= self.retries:
                    break
                await asyncio.sleep(self.retry_backoff_seconds * (attempt + 1))

        if last_error is None:
            raise RuntimeError("Unknown error while calling Ollama")

        raise httpx.HTTPError(str(last_error)) from last_error
