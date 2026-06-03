"""
Admin Router (Stub).
"""
# pyrefly: ignore [missing-import]
from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("")
async def get_admin_status():
    return {}
