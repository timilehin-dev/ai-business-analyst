"""
Briefing API - Sense Loop endpoints.

GET  /api/briefing          -> latest stored briefing
POST /api/briefing/generate -> run the Sense loop now (anomaly scan + briefing)
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from agent.sense.briefing import briefing_store, generate_briefing

router = APIRouter(prefix="/briefing", tags=["briefing"])


@router.get("")
async def get_briefing() -> Dict[str, Any]:
    """Return the latest briefing (or an empty state if none yet)."""
    latest = briefing_store.latest()
    if latest is None:
        return {
            "briefing": None,
            "message": "No briefing yet. The nightly briefing runs automatically at 6 AM — or generate one now.",
        }
    return {"briefing": latest, "message": None}


@router.get("/history")
async def briefing_history(limit: int = 10) -> Dict[str, Any]:
    """Recent briefings."""
    return {"briefings": briefing_store.list(limit=limit)}


@router.post("/generate")
async def generate_now() -> Dict[str, Any]:
    """Run the Sense loop immediately and store the result."""
    from api.main import analyst

    if analyst is None:
        raise HTTPException(
            status_code=503,
            detail="Analyst is not initialized. Complete the setup wizard first.",
        )
    briefing = await generate_briefing(analyst)
    return {"success": True, "briefing": briefing}