"""
Main API router wiring v1 endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.folders import router as folders_router
from app.api.v1.documents import router as documents_router
from app.api.v1.chat import router as chat_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.admin import router as admin_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(folders_router)
api_router.include_router(documents_router)
api_router.include_router(chat_router)
api_router.include_router(analytics_router)
api_router.include_router(evaluation_router)
api_router.include_router(admin_router)
