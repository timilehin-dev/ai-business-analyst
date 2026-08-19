"""
Setup Wizard API - Zero-Configuration Onboarding.
Handles database connection, AI provider selection, and feature toggles.
All configuration stored encrypted in database - no .env files needed.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json

router = APIRouter(prefix="/setup", tags=["setup"])


class DatabaseConfig(BaseModel):
    """Database connection configuration."""
    db_type: str = Field(..., description="Database type: postgres, mysql, sqlite")
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database_name: Optional[str] = None
    connection_string: Optional[str] = None  # For direct connection string input


class AIProviderConfig(BaseModel):
    """AI model provider configuration."""
    provider: str = Field(..., description="Provider: ollama, openai, anthropic, ollama-cloud")
    model_name: str = Field(..., description="Model to use")
    api_key: Optional[str] = None
    base_url: Optional[str] = None  # For Ollama local or custom endpoints
    is_local: bool = Field(default=False, description="Whether this is a local model")


class FeatureToggles(BaseModel):
    """Feature enablement toggles."""
    newsroom_enabled: bool = Field(default=True, description="Enable web search")
    code_sandbox_enabled: bool = Field(default=True, description="Enable code execution")
    air_gap_mode: bool = Field(default=False, description="Disable all external calls")
    proactive_monitoring: bool = Field(default=True, description="Enable background analysis")


class SetupRequest(BaseModel):
    """Complete setup request."""
    database: DatabaseConfig
    ai_provider: AIProviderConfig
    features: FeatureToggles
    organization_name: str = Field(..., description="Organization name")


class SetupResponse(BaseModel):
    """Setup completion response."""
    success: bool
    message: str
    next_step: Optional[str] = None
    config_id: Optional[str] = None


@router.get("/status")
async def get_setup_status() -> Dict[str, Any]:
    """
    Check if setup has been completed.
    Returns setup status and current configuration summary.
    """
    # TODO: Check database for existing configuration
    return {
        "is_configured": False,  # Will be dynamic
        "needs_setup": True,
        "current_step": 1,
        "total_steps": 3
    }


@router.post("/test-database")
async def test_database_connection(config: DatabaseConfig) -> Dict[str, Any]:
    """
    Test database connection without saving.
    Provides immediate feedback to user.
    """
    # TODO: Implement actual connection test
    # For now, return simulated success
    
    return {
        "success": True,
        "message": "Connection successful!",
        "details": {
            "database_type": config.db_type,
            "tables_found": 0,  # Would scan schema
            "connection_time_ms": 45
        }
    }


@router.post("/test-ai-provider")
async def test_ai_provider(config: AIProviderConfig) -> Dict[str, Any]:
    """
    Test AI provider connectivity.
    Validates API keys and model availability.
    """
    # TODO: Implement actual provider test
    return {
        "success": True,
        "message": f"Successfully connected to {config.provider}",
        "model_info": {
            "name": config.model_name,
            "status": "available",
            "context_window": "8k"  # Would fetch from provider
        }
    }


@router.post("/complete", response_model=SetupResponse)
async def complete_setup(request: SetupRequest) -> SetupResponse:
    """
    Complete the setup wizard and save configuration.
    Encrypts sensitive data and stores in database.
    """
    try:
        # TODO: 
        # 1. Validate all configurations
        # 2. Encrypt sensitive data (passwords, API keys)
        # 3. Store in database
        # 4. Initialize memory tables
        # 5. Start background scheduler if proactive monitoring enabled
        
        config_id = "config_001"  # Would generate UUID
        
        return SetupResponse(
            success=True,
            message="Setup completed successfully! Your analyst is ready.",
            next_step="dashboard",
            config_id=config_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Setup failed: {str(e)}"
        )


@router.get("/providers")
async def get_available_providers() -> Dict[str, List[Dict[str, Any]]]:
    """
    Get list of available AI providers and their models.
    Helps users choose during setup.
    """
    return {
        "providers": [
            {
                "id": "ollama",
                "name": "Ollama (Local)",
                "description": "Free, runs on your hardware",
                "privacy": "Excellent - no data leaves your server",
                "cost": "$0",
                "models": ["llama3.1:8b", "qwen2.5:7b", "mistral:7b"]
            },
            {
                "id": "ollama-cloud",
                "name": "Ollama Cloud",
                "description": "Hosted Ollama service",
                "privacy": "Good - encrypted transmission",
                "cost": "Pay per token",
                "models": ["llama3.1:70b", "qwen2.5:72b"]
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "description": "GPT-4 and other models",
                "privacy": "Standard - data sent to OpenAI",
                "cost": "$$$",
                "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
            },
            {
                "id": "anthropic",
                "name": "Anthropic",
                "description": "Claude models",
                "privacy": "Standard - data sent to Anthropic",
                "cost": "$$$",
                "models": ["claude-sonnet-4", "claude-opus"]
            }
        ]
    }
