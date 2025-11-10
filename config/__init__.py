"""
Configuration module
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Kavita Configuration
    kavita_base_url: str = "http://localhost:5000"
    kavita_api_key: str = ""  # Required API key
    kavita_plugin_name: str = "ESP32Reader"  # Plugin name for authentication

    # Display Configuration (4.2" e-paper = 400x300)
    display_width: int = 400
    display_height: int = 300
    font_size: int = 16
    font_path: Optional[str] = None

    # Server Configuration
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Create global settings instance
settings = Settings()

__all__ = ["settings", "Settings"]
