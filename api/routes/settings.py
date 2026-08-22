"""
Settings API — read and update system preferences.
"""
from typing import Any, Dict, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from agent.memory.database import db_manager

router = APIRouter(prefix="/settings", tags=["settings"])


class AIProviderUpdate(BaseModel):
    provider: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    models: Optional[Dict[str, str]] = None


class FeatureUpdate(BaseModel):
    newsroom: Optional[bool] = None
    code_sandbox: Optional[bool] = None
    air_gap: Optional[bool] = None


class GeneralUpdate(BaseModel):
    organization_name: Optional[str] = None
    briefing_hour: Optional[int] = None
    briefing_timezone: Optional[str] = None


@router.get("")
async def get_settings() -> Dict[str, Any]:
    """Return all current settings."""
    features = db_manager.get_config("features", is_sensitive=False) or {}
    return {
        "organization": {
            "name": db_manager.get_config("organization_name", is_sensitive=False) or "My Organization",
        },
        "ai_provider": {
            "provider": db_manager.get_config("ai_provider", is_sensitive=False) or "ollama-local",
            "base_url": db_manager.get_config("base_url", is_sensitive=False),
            "has_api_key": bool(db_manager.get_config("api_key", is_sensitive=True)),
            "models": db_manager.get_config("models", is_sensitive=False) or {},
        },
        "database": {
            "url_set": bool(db_manager.get_config("database_url", is_sensitive=False)),
        },
        "features": {
            "newsroom": features.get("newsroom", True),
            "code_sandbox": features.get("code_sandbox", True),
            "air_gap": features.get("air_gap", False),
        },
    }


@router.put("/ai-provider")
async def update_ai_provider(update: AIProviderUpdate) -> Dict[str, Any]:
    if update.provider is not None:
        db_manager.save_config("ai_provider", update.provider, is_sensitive=False)
    if update.api_key is not None:
        db_manager.save_config("api_key", update.api_key, is_sensitive=True)
    if update.base_url is not None:
        db_manager.save_config("base_url", update.base_url, is_sensitive=False)
    if update.models is not None:
        existing = db_manager.get_config("models", is_sensitive=False) or {}
        existing.update(update.models)
        db_manager.save_config("models", existing, is_sensitive=False)
    from api.main import reinitialize_analyst
    reinitialize_analyst()
    return {"success": True, "message": "AI provider updated and analyst re-initialized."}


@router.put("/features")
async def update_features(update: FeatureUpdate) -> Dict[str, Any]:
    current = db_manager.get_config("features", is_sensitive=False) or {}
    if update.newsroom is not None:
        current["newsroom"] = update.newsroom
    if update.code_sandbox is not None:
        current["code_sandbox"] = update.code_sandbox
    if update.air_gap is not None:
        current["air_gap"] = update.air_gap
    db_manager.save_config("features", current, is_sensitive=False)
    return {"success": True, "features": current}


@router.put("/general")
async def update_general(update: GeneralUpdate) -> Dict[str, Any]:
    if update.organization_name is not None:
        db_manager.save_config("organization_name", update.organization_name, is_sensitive=False)
    return {"success": True, "message": "General settings updated."}