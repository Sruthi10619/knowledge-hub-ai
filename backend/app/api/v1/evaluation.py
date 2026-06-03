"""
Evaluation Router (Stub).
"""
from fastapi import APIRouter

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

@router.get("")
async def get_evaluation():
    return {}
