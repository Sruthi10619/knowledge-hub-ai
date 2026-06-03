"""Custom exception classes and exception handlers."""

from __future__ import annotations

from fastapi import HTTPException, status


class KnowledgeHubException(Exception):
    """Base exception for Knowledge Hub AI."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class DocumentProcessingError(KnowledgeHubException):
    """Raised when document processing fails."""

    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class RAGPipelineError(KnowledgeHubException):
    """Raised when the RAG pipeline encounters an error."""

    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class LLMProviderError(KnowledgeHubException):
    """Raised when an LLM provider call fails."""

    def __init__(self, message: str):
        super().__init__(message, status_code=502)


class FolderNotFoundError(KnowledgeHubException):
    """Raised when a folder is not found."""

    def __init__(self, folder_id: str):
        super().__init__(f"Folder '{folder_id}' not found", status_code=404)


class DocumentNotFoundError(KnowledgeHubException):
    """Raised when a document is not found."""

    def __init__(self, doc_id: str):
        super().__init__(f"Document '{doc_id}' not found", status_code=404)


class GuardrailViolation(KnowledgeHubException):
    """Raised when a safety guardrail is triggered."""

    def __init__(self, message: str = "Request blocked by safety guardrails"):
        super().__init__(message, status_code=400)


class RateLimitExceeded(KnowledgeHubException):
    """Raised when rate limit is exceeded."""

    def __init__(self):
        super().__init__("Rate limit exceeded. Please try again later.", status_code=429)
