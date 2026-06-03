"""
Security utilities: JWT tokens, password hashing, RBAC, file validation.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
import bcrypt
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.base import get_db

# ── Password hashing ────────────────────────────────────────────────────
security_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt directly."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a password against its hash using bcrypt directly."""
    try:
        plain_bytes = plain.encode("utf-8")
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False


# ── JWT Tokens ───────────────────────────────────────────────────────────
def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Current User Dependency ─────────────────────────────────────────────
async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Extract and validate the current user from the JWT token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    user_id: str = payload.get("sub")
    token_type: str = payload.get("type", "access")

    if not user_id or token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    from app.db.models.user import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


# ── RBAC ─────────────────────────────────────────────────────────────────
def require_role(*roles: str):
    """Dependency factory: restrict endpoint to specific roles."""

    async def _check(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(roles)}",
            )
        return current_user

    return _check


# ── File Validation ──────────────────────────────────────────────────────
MAGIC_BYTES = {
    "pdf": b"%PDF",
    "docx": b"PK\x03\x04",
    "csv": None,  # Text-based, no magic bytes
    "txt": None,
    "md": None,
}


def validate_file_upload(
    filename: str,
    content: bytes,
    max_size_mb: int = 50,
) -> tuple[bool, str]:
    """
    Validate an uploaded file for type and size.
    Returns (is_valid, error_message).
    """
    settings = get_settings()

    # Check file extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in settings.ALLOWED_FILE_TYPES:
        return False, f"File type '.{ext}' is not allowed. Allowed: {settings.ALLOWED_FILE_TYPES}"

    # Check file size
    size_mb = len(content) / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"File size ({size_mb:.1f}MB) exceeds maximum ({max_size_mb}MB)"

    # Check magic bytes for binary files
    expected_magic = MAGIC_BYTES.get(ext)
    if expected_magic and not content.startswith(expected_magic):
        return False, f"File content does not match expected format for '.{ext}'"

    # Basic malicious content check
    if ext in ("txt", "md", "csv"):
        try:
            text = content.decode("utf-8", errors="ignore")
            # Check for script injection in text files
            suspicious_patterns = [
                r"<script[\s>]",
                r"javascript:",
                r"on\w+\s*=",
            ]
            for pattern in suspicious_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return False, "File contains potentially malicious content"
        except Exception:
            pass

    return True, ""


def sanitize_filename(filename: str | None) -> str:
    """
    Strip path components and unsafe characters from an upload filename.
    Falls back to upload_<uuid>.bin when the result would be empty.
    """
    import uuid

    if not filename or not str(filename).strip():
        return f"upload_{uuid.uuid4().hex[:12]}.bin"

    # Use basename only (blocks path traversal via slashes)
    name = Path(filename).name
    name = name.replace("\x00", "").strip()

    # Remove parent-directory segments and collapse unsafe chars
    name = name.replace("..", "")
    safe = re.sub(r'[<>:"|?*\x00-\x1f]', "_", name).strip("._ ")

    if not safe or safe in (".", ".."):
        ext = ""
        if "." in filename:
            ext = filename.rsplit(".", 1)[-1].lower()
            if ext in get_settings().ALLOWED_FILE_TYPES:
                return f"upload_{uuid.uuid4().hex[:12]}.{ext}"
        return f"upload_{uuid.uuid4().hex[:12]}.bin"

    return safe


def compute_file_hash(content: bytes) -> str:
    """Compute SHA-256 hash of file content for deduplication."""
    return hashlib.sha256(content).hexdigest()
