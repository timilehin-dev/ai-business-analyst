"""
Configuration management for AI Business Analyst.
Supports environment variables and YAML config files.
"""
from pydantic_settings import BaseSettings
from typing import Optional, Dict, List
import os


class ModelConfig(BaseSettings):
    """Model provider configuration with task-based routing."""
    reasoning: str = "ollama/llama3.1:8b"
    sql: str = "ollama/qwen2.5-coder:7b"
    embedding: str = "ollama/bge-m3"
    fallback: str = "ollama-cloud/llama3.1:70b"

    class Config:
        env_prefix = "MODEL_"


class DatabaseConfig(BaseSettings):
    """Database connection settings."""
    url: str = "sqlite:///./data/analyst.db"
    pool_size: int = 10
    max_overflow: int = 20

    class Config:
        env_prefix = "DATABASE_"


class SecurityConfig(BaseSettings):
    """Security and access control settings."""
    read_only: bool = True
    air_gap_mode: bool = False
    pii_masking: bool = True
    allowed_schemas: List[str] = []
    blocked_tables: List[str] = []
    audit_log_path: str = "./data/audit.log"

    class Config:
        env_prefix = "SECURITY_"


class NewsroomConfig(BaseSettings):
    """Web search configuration."""
    enabled: bool = True
    max_results: int = 5
    timeout_seconds: int = 10

    class Config:
        env_prefix = "NEWSROOM_"


class Settings(BaseSettings):
    """Main application settings."""
    # App
    app_name: str = "AI Business Analyst"
    debug: bool = False
    data_dir: str = "./data"

    # Components
    models: ModelConfig = ModelConfig()
    database: DatabaseConfig = DatabaseConfig()
    security: SecurityConfig = SecurityConfig()
    newsroom: NewsroomConfig = NewsroomConfig()

    # Sense loop (nightly briefing)
    briefing_hour: int = 6
    briefing_timezone: str = "UTC"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
