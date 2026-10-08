"""
Application configuration.
Values can be overridden via environment variables or a .env file.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    PROJECT_NAME: str = "Geospatial File Measurement API"

    # Where uploaded files are stored temporarily before processing
    UPLOAD_DIR: Path = Path("uploads")

    # SQLite database URL (relative path; use absolute or postgresql:// for prod)
    DATABASE_URL: str = "sqlite:///./geo_api.db"

    # Maximum file size accepted (bytes).  Default = 50 MB.
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024

    # Allowed MIME / extension combos
    ALLOWED_EXTENSIONS: list[str] = [".zip", ".kml"]


settings = Settings()

# Make sure the upload directory exists
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
