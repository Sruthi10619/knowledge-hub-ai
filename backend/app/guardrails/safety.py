"""
Input and Output Safety Guardrail Pipeline.
"""

from __future__ import annotations

from app.core.exceptions import GuardrailViolation
from app.guardrails.injection import InjectionDetector
from app.guardrails.toxicity import ToxicityScanner


class SafetyGuardrails:
    @classmethod
    def verify_input(cls, user_query: str) -> None:
        """
        Runs injection and toxicity checks on incoming user queries.
        Raises GuardrailViolation if unsafe.
        """
        # 1. Prompt Injection check
        if InjectionDetector.detect(user_query):
            raise GuardrailViolation("Request blocked: Suspicious prompt injection pattern detected.")

        # 2. Toxicity check
        if ToxicityScanner.contains_toxic_content(user_query):
            raise GuardrailViolation("Request blocked: Query violates the safety policy.")

    @classmethod
    def verify_output(cls, assistant_response: str) -> None:
        """
        Runs safety checks on LLM generated answers before returning to user.
        Raises GuardrailViolation if unsafe.
        """
        # Toxicity check on output
        if ToxicityScanner.contains_toxic_content(assistant_response):
            raise GuardrailViolation("Response blocked: Generated answer violates the safety policy.")
