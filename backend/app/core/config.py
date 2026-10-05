"""
Application settings loaded from environment variables.

Uses pydantic-settings to read the root .env file.
"""

from pathlib import Path
from pydantic_settings import BaseSettings


# Resolve the project root (.env lives three levels above backend/app/core/)
_ROOT_DIR = Path(__file__).resolve().parents[3]
_ENV_FILE = _ROOT_DIR / ".env"


class Settings(BaseSettings):
    """Central configuration – values come from environment variables or .env file."""

    MONGODB_URI: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    DEFAULT_DEMO_PASSWORD: str = "demo123"
    CORS_ORIGINS: str = ""

    model_config = {
        "env_file": str(_ENV_FILE) if _ENV_FILE.exists() else None,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def allowed_origins(self) -> list[str]:
        defaults = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
        if self.CORS_ORIGINS and self.CORS_ORIGINS.strip():
            extras = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
            for item in extras:
                if item not in defaults:
                    defaults.append(item)
        return defaults


# Singleton instance used throughout the application
settings = Settings()
