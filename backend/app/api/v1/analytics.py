"""
Analytics API Endpoints.
"""

from __future__ import annotations

from typing import Any, Dict
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.dependencies import get_db_session, get_current_active_user
from app.db.models.user import User
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


class EventLogRequest(BaseModel):
    event_type: str
    event_data: Dict[str, Any] = {}


@router.get("/dashboard")
async def get_dashboard_analytics(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieves all aggregated stats and metrics for the user's dashboard view."""
    return await AnalyticsService.get_dashboard_stats(db=db, user_id=current_user.id)


@router.post("/events")
async def log_analytics_event(
    payload: EventLogRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
):
    """Registers an interaction event inside the system analytics logger."""
    event = await AnalyticsService.log_event(
        db=db,
        user_id=current_user.id,
        event_type=payload.event_type,
        event_data=payload.event_data
    )
    return {"status": "logged", "event_id": event.id}
