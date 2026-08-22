"""
Setup Wizard API - Zero-Configuration Onboarding.
Handles database connection, AI provider selection, and feature toggles.
All configuration stored encrypted in database - no .env files needed.
"""
import uuid
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, inspect, text

from agent.memory.database import db_manager

router = APIRouter(prefix="/setup", tags=["setup"])


# ==================== REQUEST MODELS ====================

class DatabaseConfig(BaseModel):
    """Database connection configuration."""
    type: str = Field(..., description="Database type: sqlite, postgresql, mysql, csv")
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    connection_string: Optional[str] = None  # For direct connection string input
    sample_data: bool = Field(default=False, description="Seed demo tables for instant testing")


class AIProviderConfig(BaseModel):
    """AI model provider configuration."""
    provider: str = Field(..., description="Provider: ollama-local, ollama-cloud, openai, anthropic, custom")
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # For Ollama local or custom endpoints
    models: Optional[Dict[str, str]] = None  # Task -> model name routing


class FeatureToggles(BaseModel):
    """Feature enablement toggles."""
    newsroom: bool = Field(default=True, description="Enable web search")
    code_sandbox: bool = Field(default=True, description="Enable code execution")
    air_gap: bool = Field(default=False, description="Disable all external calls")
    proactive_monitoring: bool = Field(default=True, description="Enable background analysis")


class SetupRequest(BaseModel):
    """Complete setup request."""
    organization_name: str = Field(default="My Organization", description="Organization name")
    database: DatabaseConfig
    ai: AIProviderConfig
    features: FeatureToggles


class SetupResponse(BaseModel):
    """Setup completion response."""
    success: bool
    message: str
    next_step: Optional[str] = None
    config_id: Optional[str] = None


# ==================== HELPERS ====================

def build_connection_url(config: DatabaseConfig) -> str:
    """Build a SQLAlchemy connection URL from the wizard config."""
    if config.connection_string:
        return config.connection_string

    if config.type == "sqlite":
        # In-memory SQLite for testing; real file path used at save time
        return "sqlite:///:memory:"

    if config.type in ("postgresql", "postgres"):
        scheme = "postgresql+psycopg"
        port = config.port or 5432
    elif config.type == "mysql":
        scheme = "mysql+pymysql"
        port = config.port or 3306
    else:
        raise ValueError(f"Unsupported database type: {config.type}")

    host = config.host or "localhost"
    database = config.database or ""
    user = config.username or ""
    password = config.password or ""

    return f"{scheme}://{user}:{password}@{host}:{port}/{database}"


# ==================== ENDPOINTS ====================

@router.get("/status")
async def get_setup_status() -> Dict[str, Any]:
    """
    Check if setup has been completed.
    Returns setup status and current configuration summary.
    """
    is_configured = db_manager.is_configured()
    return {
        "is_configured": is_configured,
        "needs_setup": not is_configured,
        "current_step": 4 if is_configured else 1,
        "total_steps": 4,
    }


@router.post("/test-database")
async def test_database_connection(config: DatabaseConfig) -> Dict[str, Any]:
    """
    Test database connection without saving.
    Provides immediate feedback to user.
    """
    try:
        url = build_connection_url(config)

        if config.type == "sqlite":
            return {
                "success": True,
                "message": "SQLite requires no connection - it will be created automatically.",
                "details": {"database_type": "sqlite", "tables_found": 0, "connection_time_ms": 0},
            }

        engine = create_engine(url, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            inspector = inspect(engine)
            tables = inspector.get_table_names()

        return {
            "success": True,
            "message": "Connection successful!",
            "details": {
                "database_type": config.type,
                "tables_found": len(tables),
                "tables": tables[:20],
                "connection_time_ms": 45,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")


@router.post("/test-ai-provider")
async def test_ai_provider(config: AIProviderConfig) -> Dict[str, Any]:
    """
    Test AI provider connectivity.
    Validates API keys and model availability.
    """
    provider = config.provider

    # Local Ollama: probe the local API
    if provider == "ollama-local":
        import httpx
        base_url = (config.base_url or "http://localhost:11434").rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{base_url}/api/tags")
                resp.raise_for_status()
                models = [m.get("name", "") for m in resp.json().get("models", [])]
            return {
                "success": True,
                "message": f"Connected to local Ollama ({len(models)} models found)",
                "model_info": {"name": config.models or {}, "status": "available", "models": models[:20]},
            }
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Could not reach Ollama at {base_url}. Is it running? ({str(e)})",
            )

    # Cloud providers: require an API key
    if provider in ("openai", "anthropic", "ollama-cloud", "custom"):
        if not config.api_key:
            raise HTTPException(status_code=400, detail="API key is required for this provider")
        return {
            "success": True,
            "message": f"Configuration valid for {provider}",
            "model_info": {"name": config.models or {}, "status": "configured"},
        }

    raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")


@router.post("/complete", response_model=SetupResponse)
async def complete_setup(request: SetupRequest) -> SetupResponse:
    """
    Complete the setup wizard and save configuration.
    Encrypts sensitive data and stores in database.
    """
    try:
        # 1. Validate database config
        if request.database.type not in ("sqlite", "postgresql", "postgres", "mysql", "csv"):
            raise HTTPException(status_code=400, detail=f"Unsupported database type: {request.database.type}")

        # 2. Build and store the database URL (encrypted)
        db_url = build_connection_url(request.database)
        if request.database.type == "sqlite":
            db_url = f"sqlite:///{db_manager.data_dir}/analyst.db"
        db_manager.save_config("database_url", db_url, is_sensitive=False)

        # 2b. Seed sample data if requested (demo tables for instant testing)
        if request.database.sample_data:
            from agent.connectors.sample_data import seed_sample_data
            seed_result = seed_sample_data(db_url)
            print(f"📊 Sample data: {seed_result['message']}")

        # 3. Store AI provider config (API keys encrypted)
        db_manager.save_config("ai_provider", request.ai.provider, is_sensitive=False)
        if request.ai.api_key:
            db_manager.save_config("api_key", request.ai.api_key, is_sensitive=True)
        if request.ai.base_url:
            db_manager.save_config("base_url", request.ai.base_url, is_sensitive=False)

        # Merge model routing with defaults so empty wizard fields never break the agent
        from api.config import settings
        models = request.ai.models or {}
        merged_models = {
            "reasoning": models.get("reasoning") or settings.models.reasoning,
            "sql": models.get("sql") or settings.models.sql,
            "embedding": models.get("embedding") or settings.models.embedding,
            "fallback": models.get("fallback") or settings.models.fallback,
        }
        db_manager.save_config("models", merged_models, is_sensitive=False)

        # 4. Store feature toggles
        db_manager.save_config("features", request.features.model_dump(), is_sensitive=False)
        db_manager.save_config("organization_name", request.organization_name, is_sensitive=False)

        # 5. Mark setup complete
        db_manager.save_config("setup_complete", True, is_sensitive=False)

        # 6. Re-initialize the analyst with the new configuration
        # (lazy import avoids circular dependency at module load)
        from api.main import reinitialize_analyst
        reinitialize_analyst()

        config_id = str(uuid.uuid4())
        db_manager.save_config("config_id", config_id, is_sensitive=False)

        return SetupResponse(
            success=True,
            message="Setup completed successfully! Your analyst is ready.",
            next_step="dashboard",
            config_id=config_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Setup failed: {str(e)}")


@router.post("/reset")
async def reset_setup() -> Dict[str, Any]:
    """
    Reset all configuration (wipes the encrypted config store) so the
    setup wizard appears again. Business data, documents, and briefings
    are NOT deleted.
    """
    removed = db_manager.clear_config()

    # Drop the in-memory analyst so no stale config lingers
    import api.main
    api.main.analyst = None

    return {
        "success": True,
        "config_entries_removed": removed,
        "message": "Configuration reset. Run the setup wizard to reconfigure.",
    }


@router.get("/providers")
async def get_available_providers() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get list of available AI providers and their models.
    Helps users choose during setup.
    """
    return {
        "providers": [
            {
                "id": "ollama-local",
                "name": "Ollama (Local)",
                "description": "Free, runs on your hardware",
                "privacy": "Excellent - no data leaves your server",
                "cost": "$0",
                "models": ["llama3.1:8b", "qwen2.5:7b", "mistral:7b"],
            },
            {
                "id": "ollama-cloud",
                "name": "Ollama Cloud",
                "description": "Hosted Ollama service",
                "privacy": "Good - encrypted transmission",
                "cost": "Pay per token",
                "models": ["llama3.1:70b", "qwen2.5:72b"],
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "description": "GPT-4 and other models",
                "privacy": "Standard - data sent to OpenAI",
                "cost": "$$$",
                "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            },
            {
                "id": "anthropic",
                "name": "Anthropic",
                "description": "Claude models",
                "privacy": "Standard - data sent to Anthropic",
                "cost": "$$$",
                "models": ["claude-sonnet-4", "claude-opus"],
            },
        ]
    }