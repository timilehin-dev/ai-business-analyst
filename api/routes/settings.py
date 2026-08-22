"""
Settings API — read and update system preferences.

Feature and provider changes rebuild the analyst immediately so a toggle
takes effect without a restart.
"""
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent.memory.database import db_manager
from agent.memory.memory import memory_store
from api.config import settings as app_settings

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
    proactive_monitoring: Optional[bool] = None


class GeneralUpdate(BaseModel):
    organization_name: Optional[str] = None
    briefing_hour: Optional[int] = Field(default=None, ge=0, le=23)
    briefing_timezone: Optional[str] = None


def _general_config() -> Dict[str, Any]:
    return db_manager.get_config("general", is_sensitive=False) or {}


@router.get("")
async def get_settings() -> Dict[str, Any]:
    """Return all current settings."""
    features = db_manager.get_config("features", is_sensitive=False) or {}
    general = _general_config()
    return {
        "organization": {
            "name": db_manager.get_config("organization_name", is_sensitive=False)
            or "My Organization",
        },
        "ai_provider": {
            "provider": db_manager.get_config("ai_provider", is_sensitive=False)
            or "ollama-local",
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
            "proactive_monitoring": features.get("proactive_monitoring", True),
        },
        "briefing": {
            "hour": general.get("briefing_hour", app_settings.briefing_hour),
            "timezone": general.get("briefing_timezone", app_settings.briefing_timezone),
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
    memory_store.audit(
        "settings.ai_provider_updated",
        {"provider": update.provider, "models": update.models},
        actor="user",
    )
    return {"success": True, "message": "AI provider updated and analyst re-initialized."}


@router.put("/features")
async def update_features(update: FeatureUpdate) -> Dict[str, Any]:
    current = db_manager.get_config("features", is_sensitive=False) or {}
    for field_name, value in update.model_dump(exclude_none=True).items():
        current[field_name] = value
    db_manager.save_config("features", current, is_sensitive=False)

    # Newsroom, air-gap, and sandbox are baked into the graph at build time,
    # so the analyst must be rebuilt for a toggle to have any effect.
    from api.main import reinitialize_analyst

    reinitialize_analyst()
    memory_store.audit("settings.features_updated", current, actor="user")

    return {
        "success": True,
        "features": current,
        "message": "Features updated. Proactive monitoring changes apply on next restart.",
    }


@router.put("/general")
async def update_general(update: GeneralUpdate) -> Dict[str, Any]:
    if update.organization_name is not None:
        db_manager.save_config(
            "organization_name", update.organization_name, is_sensitive=False
        )

    general = _general_config()
    if update.briefing_hour is not None:
        general["briefing_hour"] = update.briefing_hour
    if update.briefing_timezone is not None:
        try:
            ZoneInfo(update.briefing_timezone)
        except (ZoneInfoNotFoundError, ValueError) as e:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown timezone '{update.briefing_timezone}'",
            ) from e
        general["briefing_timezone"] = update.briefing_timezone

    if general:
        db_manager.save_config("general", general, is_sensitive=False)

    memory_store.audit("settings.general_updated", general, actor="user")
    return {
        "success": True,
        "message": "General settings updated. Briefing schedule applies on next restart.",
        "briefing": {
            "hour": general.get("briefing_hour", app_settings.briefing_hour),
            "timezone": general.get("briefing_timezone", app_settings.briefing_timezone),
        },
    }
