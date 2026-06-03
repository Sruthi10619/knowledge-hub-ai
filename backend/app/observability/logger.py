"""
Lightweight Structured Logging & Observability Engine.
Captures RAG metrics, execution steps, and formats logs into human-readable & JSON streams.
"""

from __future__ import annotations

import json
import logging
import time
import os
from typing import Any, Dict, Optional
from datetime import datetime

# Root workspace directory for writing structured log files
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "logs")

class StructuredObservabilityLogger:
    _initialized = False

    @classmethod
    def initialize(cls):
        if cls._initialized:
            return
        os.makedirs(LOGS_DIR, exist_ok=True)
        cls._initialized = True

    @classmethod
    def log_rag_step(
        cls,
        conversation_id: str,
        step_name: str,
        latency_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Logs a specific sub-component RAG step latency and parameters."""
        cls.initialize()
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "conversation_id": conversation_id,
            "type": "rag_step",
            "step": step_name,
            "latency_ms": round(latency_ms, 2),
            "metadata": metadata or {}
        }
        
        # Log to Python logging framework
        logger = logging.getLogger("app.observability")
        logger.info(f"[RAG STEP] {step_name} completed in {latency_ms:.2f}ms for conv {conversation_id}")

        # Append to JSON lines file
        log_file = os.path.join(LOGS_DIR, "rag_steps.jsonl")
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to write structured log to file: {e}")

    @classmethod
    def log_llm_execution(
        cls,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        success: bool,
        error: Optional[str] = None
    ):
        """Logs an LLM call for usage tracking and billing approximation."""
        cls.initialize()
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "llm_call",
            "provider": provider,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": round(latency_ms, 2),
            "success": success,
            "error": error
        }
        
        logger = logging.getLogger("app.observability")
        if success:
            logger.info(f"[LLM CALL] {provider} generated {completion_tokens} tokens in {latency_ms:.2f}ms")
        else:
            logger.error(f"[LLM CALL FAILED] {provider} failed after {latency_ms:.2f}ms: {error}")

        log_file = os.path.join(LOGS_DIR, "llm_calls.jsonl")
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.error(f"Failed to write structured log to file: {e}")
