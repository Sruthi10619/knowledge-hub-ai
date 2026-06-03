"""
Hugging Face Inference API LLM Provider implementation.
"""

from __future__ import annotations

import json
from typing import AsyncGenerator, Dict, List, Optional
import httpx

from app.config import get_settings
from app.llm.provider import LLMProvider
from app.core.exceptions import LLMProviderError


class HuggingFaceProvider(LLMProvider):
    def __init__(self):
        settings = get_settings()
        if not settings.HF_API_TOKEN:
            raise LLMProviderError("HF_API_TOKEN is not set in configuration")
        self.token = settings.HF_API_TOKEN
        self.model = settings.HF_MODEL
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model}"
        self.headers = {"Authorization": f"Bearer {self.token}"}

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        # Standard chat template fallback for open models
        # For simplicity, we join prompt roles or format with simple instruction
        prompt = self._format_messages_to_prompt(messages)
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": max(temperature, 0.01),
                "max_new_tokens": max_tokens or 1024,
                "return_full_text": False
            }
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    raise LLMProviderError(f"HF API returned status {response.status_code}: {response.text}")
                
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", "")
                elif isinstance(result, dict):
                    return result.get("generated_text", "")
                return str(result)
        except Exception as e:
            raise LLMProviderError(f"Hugging Face generation failed: {str(e)}")

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        # Hugging Face Inference API supports streaming via SSE.
        # However, for simplicity and cross-compatibility with free Hugging Face API models, 
        # we will generate the full text and yield in chunks, simulating streaming if SSE fails.
        # Alternatively, we can use client.stream("POST", ...)
        # Let's implement actual streaming for high performance.
        prompt = self._format_messages_to_prompt(messages)
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": max(temperature, 0.01),
                "max_new_tokens": max_tokens or 1024,
                "return_full_text": False
            },
            "stream": True
        }

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    self.api_url,
                    json=payload,
                    headers=self.headers,
                    timeout=30.0
                ) as response:
                    if response.status_code != 200:
                        raise LLMProviderError(f"HF API stream status {response.status_code}")
                    
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data:"):
                            try:
                                data = json.loads(line[5:])
                                token_text = data.get("token", {}).get("text", "")
                                if token_text:
                                    yield token_text
                            except Exception:
                                pass
        except Exception:
            # Fallback: non-streaming generation broken into chunks
            full_text = await self.generate(messages, temperature, max_tokens)
            # Yield in smaller chunks
            chunk_size = 8
            for i in range(0, len(full_text), chunk_size):
                yield full_text[i:i+chunk_size]

    def _format_messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        prompt = ""
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                prompt += f"System: {content}\n\n"
            elif role == "user":
                prompt += f"User: {content}\n\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n\n"
        prompt += "Assistant: "
        return prompt
