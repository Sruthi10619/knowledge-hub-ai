"""
Anthropic LLM Provider implementation.
"""

from __future__ import annotations

from typing import AsyncGenerator, Dict, List, Optional
from anthropic import AsyncAnthropic

from app.config import get_settings
from app.llm.provider import LLMProvider
from app.core.exceptions import LLMProviderError


class AnthropicProvider(LLMProvider):
    def __init__(self):
        settings = get_settings()
        if not settings.ANTHROPIC_API_KEY:
            raise LLMProviderError("ANTHROPIC_API_KEY is not set in configuration")
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.ANTHROPIC_MODEL

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        try:
            # Anthropic needs system prompt separately if present
            system_prompt = ""
            user_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    user_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

            kwargs = {
                "model": self.model,
                "messages": user_messages,
                "temperature": temperature,
                "max_tokens": max_tokens or 4096,
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            response = await self.client.messages.create(**kwargs)
            return response.content[0].text
        except Exception as e:
            raise LLMProviderError(f"Anthropic generation failed: {str(e)}")

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        try:
            system_prompt = ""
            user_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                else:
                    user_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

            kwargs = {
                "model": self.model,
                "messages": user_messages,
                "temperature": temperature,
                "max_tokens": max_tokens or 4096,
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            async with self.client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise LLMProviderError(f"Anthropic streaming failed: {str(e)}")
