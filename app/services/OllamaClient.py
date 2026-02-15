import httpx
from loguru import logger
from app.config import get_settings


class OllamaClient:
    """HTTP client for Ollama's OpenAI-compatible API."""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL

    async def chat_completion(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> dict:
        """
        Call Ollama's /v1/chat/completions endpoint.

        Args:
            messages: List of message dicts (role, content, etc.)
            tools: Optional list of tool definitions (OpenAI function calling format)

        Returns:
            The response dict from Ollama

        Raises:
            httpx.ConnectError: If Ollama is not reachable
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
