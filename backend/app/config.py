"""Application configuration with environment variable validation."""

from typing import Optional, List
from pydantic import BaseSettings, validator, Field
import os


class Settings(BaseSettings):
    """Application settings with validation."""

    # Environment
    ENV: str = Field(default="development", description="Environment (development, staging, production)")
    DEBUG: bool = Field(default=False, description="Enable debug mode")

    # Server
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    WORKERS: int = Field(default=1, description="Number of worker processes")

    # API
    API_VERSION: str = Field(default="v1", description="API version")

    # Authentication
    AUTH_MODE: str = Field(default="jwt_or_api_key", description="Auth mode: anonymous, api_key, jwt, jwt_or_api_key")
    API_KEY_HEADER_NAME: str = Field(default="X-API-Key", description="Header name for API key")

    # JWT Configuration
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_SECRET: Optional[str] = Field(default=None, description="JWT secret for HS256")
    JWT_PUBLIC_KEY: Optional[str] = Field(default=None, description="JWT public key for RS256")
    JWT_PUBLIC_KEY_FILE: Optional[str] = Field(default=None, description="Path to JWT public key file")
    JWT_ISSUER: Optional[str] = Field(default=None, description="Expected JWT issuer")
    JWT_AUDIENCE: Optional[str] = Field(default=None, description="Expected JWT audience")
    JWT_ROLES_CLAIM: str = Field(default="roles", description="JWT claim for user roles")
    JWT_REQUIRE_EXP: bool = Field(default=True, description="Require exp claim in JWT")

    # Document Processing
    MAX_UPLOAD_BYTES: int = Field(default=10*1024*1024, description="Max upload size in bytes")
    MAX_PDF_PAGES: int = Field(default=500, description="Max pages to extract from PDF")
    MAX_EXTRACTED_TEXT_CHARS: int = Field(default=5*1024*1024, description="Max chars from extracted text")

    # Chunking
    CHUNK_SIZE: int = Field(default=1000, description="Document chunk size in characters")
    CHUNK_OVERLAP: int = Field(default=200, description="Overlap between chunks in characters")

    # Embeddings
    EMBEDDING_MODEL: str = Field(default="all-MiniLM-L6-v2", description="Sentence transformer model")

    # Vector Store
    VECTOR_STORE_PATH: str = Field(default="./chroma_db", description="Path to persist vector store")

    # LLM Configuration
    LLM_PROVIDER: str = Field(default="openai", description="LLM provider: openai or local")
    LLM_MODEL: str = Field(default="gpt-3.5-turbo", description="LLM model name")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    LLM_TIMEOUT: int = Field(default=30, description="LLM request timeout in seconds")
    LLM_MAX_RETRIES: int = Field(default=2, description="LLM request max retries")

    # Rate Limiting
    RATE_LIMIT_UPLOAD: str = Field(default="20/hour", description="Rate limit for uploads")
    RATE_LIMIT_ASK: str = Field(default="120/hour", description="Rate limit for questions")
    RATE_LIMIT_READ: str = Field(default="600/hour", description="Rate limit for read operations")

    # Security
    CORS_ORIGINS: List[str] = Field(default=["*"], description="CORS allowed origins")
    METRICS_ENABLED: bool = Field(default=True, description="Enable Prometheus metrics")
    METRICS_TOKEN: Optional[str] = Field(default=None, description="Token required to access metrics")

    # Audit
    AUDIT_LOG_ASK: bool = Field(default=False, description="Enable audit logging for questions")

    # Stats
    STATS_ALLOWED_ROLES: Optional[List[str]] = Field(default=None, description="Roles allowed to access stats")

    @validator("ENV")
    def validate_env(cls, v: str) -> str:
        """Validate environment value."""
        valid_envs = ["development", "staging", "production"]
        if v not in valid_envs:
            raise ValueError(f"ENV must be one of {valid_envs}")
        return v

    @validator("AUTH_MODE")
    def validate_auth_mode(cls, v: str) -> str:
        """Validate auth mode."""
        valid_modes = ["anonymous", "api_key", "jwt", "jwt_or_api_key"]
        if v not in valid_modes:
            raise ValueError(f"AUTH_MODE must be one of {valid_modes}")
        return v

    @validator("LLM_PROVIDER")
    def validate_llm_provider(cls, v: str) -> str:
        """Validate LLM provider."""
        valid_providers = ["openai", "local"]
        if v not in valid_providers:
            raise ValueError(f"LLM_PROVIDER must be one of {valid_providers}")
        return v

    @validator("MAX_UPLOAD_BYTES")
    def validate_max_upload(cls, v: int) -> int:
        """Validate max upload size."""
        if v < 1024:  # At least 1KB
            raise ValueError("MAX_UPLOAD_BYTES must be at least 1024")
        if v > 100*1024*1024:  # At most 100MB
            raise ValueError("MAX_UPLOAD_BYTES must not exceed 100MB")
        return v

    @validator("CHUNK_SIZE")
    def validate_chunk_size(cls, v: int) -> int:
        """Validate chunk size."""
        if v < 100:
            raise ValueError("CHUNK_SIZE must be at least 100")
        if v > 10000:
            raise ValueError("CHUNK_SIZE must not exceed 10000")
        return v

    @validator("PORT")
    def validate_port(cls, v: int) -> int:
        """Validate port number."""
        if v < 1024 or v > 65535:
            raise ValueError("PORT must be between 1024 and 65535")
        return v

    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = True


def get_settings() -> Settings:
    """Get application settings (singleton)."""
    global _settings
    if "_settings" not in globals():
        try:
            _settings = Settings()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize settings: {e}")
    return _settings


# Load settings on module import
settings = get_settings()
