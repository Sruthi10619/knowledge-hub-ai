"""
LLM Provider Factory.
Instantiates provider implementations dynamically based on settings or explicit overrides.
"""

from __future__ import annotations

from typing import Dict, Type, Optional
from app.config import get_settings
from app.llm.provider import LLMProvider
from app.llm.groq import GroqProvider
from app.llm.openai import OpenAIProvider
from app.llm.anthropic import AnthropicProvider
from app.llm.huggingface import HuggingFaceProvider
from app.core.exceptions import LLMProviderError

PROVIDERS: Dict[str, Type[LLMProvider]] = {
    "groq": GroqProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "huggingface": HuggingFaceProvider,
}


class LLMFactory:
    @classmethod
    def get_provider(cls, name: Optional[str] = None) -> LLMProvider:
        """
        Retrieves the requested LLM provider or the default from settings.
        """
        settings = get_settings()
        provider_name = (name or settings.DEFAULT_LLM_PROVIDER).lower()

        if provider_name not in PROVIDERS:
            raise LLMProviderError(f"Unsupported LLM provider: {provider_name}")

        try:
            return PROVIDERS[provider_name]()
        except Exception as e:
            # Fallback to another configured provider if possible
            for fallback_name, provider_cls in PROVIDERS.items():
                if fallback_name == provider_name:
                    continue
                # Try to initialize
                try:
                    # Check if API key is set for fallback
                    env_key = f"{fallback_name.upper()}_API_KEY"
                    if fallback_name == "huggingface":
                        env_key = "HF_API_TOKEN"
                    
                    if getattr(settings, env_key, None):
                        return provider_cls()
                except Exception:
                    pass
            
            raise LLMProviderError(
                f"Failed to initialize LLM provider '{provider_name}' and no working fallback found. Error: {str(e)}"
            )
