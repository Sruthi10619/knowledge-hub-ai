"""
Application configuration using Pydantic Settings.
Supports dual-mode deployment: HF Spaces (SQLite) and self-hosted (PostgreSQL).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict





class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    APP_NAME: str = "Knowledge Hub AI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI-powered Knowledge Management Platform"
    DEBUG: bool = False

    # ── Paths ────────────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = Field(default=None)
    UPLOAD_DIR: Path = Field(default=None)

    @field_validator("DATA_DIR", mode="before")
    @classmethod
    def set_data_dir(cls, v, info):
        if v:
            return Path(v)
        return Path(__file__).resolve().parent.parent / "data"

    @field_validator("UPLOAD_DIR", mode="before")
    @classmethod
    def set_upload_dir(cls, v, info):
        if v:
            return Path(v)
        data_dir = info.data.get("DATA_DIR")
        if data_dir:
            return Path(data_dir) / "uploads"
        return Path(__file__).resolve().parent.parent / "data" / "uploads"

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(default=None)

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def set_database_url(cls, v, info):
        if v:
            return v
        data_dir = info.data.get("DATA_DIR") or Path(__file__).resolve().parent.parent / "data"
        return f"sqlite+aiosqlite:///{data_dir}/knowledgehub.db"

    # ── Security ─────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:7860", "https://sruthi10619-knowledge-hub-ai.hf.space"]

    # ── LLM Providers ────────────────────────────────────────────────────
    DEFAULT_LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    HF_API_TOKEN: Optional[str] = None
    HF_MODEL: str = "mistralai/Mixtral-8x7B-Instruct-v0.1"

    # ── Embeddings ───────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # ── ChromaDB ─────────────────────────────────────────────────────────
    CHROMA_PERSIST_DIR: Path = Field(default=None)

    @field_validator("CHROMA_PERSIST_DIR", mode="before")
    @classmethod
    def set_chroma_dir(cls, v, info):
        if v:
            return Path(v)
        data_dir = info.data.get("DATA_DIR")
        if data_dir:
            return Path(data_dir) / "chromadb"
        return Path(__file__).resolve().parent.parent / "data" / "chromadb"

    # ── RAG Settings ─────────────────────────────────────────────────────
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    RETRIEVAL_TOP_K: int = 5
    RERANKING_ENABLED: bool = True
    RERANKING_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    CONFIDENCE_THRESHOLD: float = 0.3


    # ── Rate Limiting ────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── File Upload ──────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_FILE_TYPES: List[str] = ["pdf", "docx", "txt", "md", "csv"]

    # ── Workers ──────────────────────────────────────────────────────────
    MAX_WORKERS: int = 4

    # ── Memory ───────────────────────────────────────────────────────────
    MAX_CONVERSATION_MEMORY_MESSAGES: int = 20
    MEMORY_TOKEN_BUDGET: int = 2000


    def ensure_directories(self) -> None:
        """Create necessary directories on startup."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
