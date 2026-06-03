"""
OpenAI LLM Provider implementation.
"""

from __future__ import annotations

from typing import AsyncGenerator, Dict, List, Optional
from openai import AsyncOpenAI

from app.config import get_settings
from app.llm.provider import LLMProvider
from app.core.exceptions import LLMProviderError


class OpenAIProvider(LLMProvider):
    def __init__(self):
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            raise LLMProviderError("OPENAI_API_KEY is not set in configuration")
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMProviderError(f"OpenAI generation failed: {str(e)}")

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens

            stream = await self.client.chat.completions.create(**kwargs)
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        except Exception as e:
            raise LLMProviderError(f"OpenAI streaming failed: {str(e)}")
