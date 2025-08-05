# config/settings.py - Simplified backward-compatible version
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing import Optional, List, Dict, Any
import os
from pathlib import Path

class SimpleSettings(BaseSettings):
    """Simplified settings that work with existing environment variables"""
    model_config = {"extra": "allow", "env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}
    
    # Database settings
    database_url: str = Field("sqlite:///jarvis.db", env="DATABASE_URL")
    database_echo: bool = Field(False, env="DATABASE_ECHO")
    
    # Security settings  
    secret_key: str = Field("change-me-in-production", env="SECRET_KEY")
    allowed_users: str = Field("admin", env="ALLOWED_USERS")
    
    # API Keys (all optional)
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    deepseek_api_key: Optional[str] = Field(None, env="DEEPSEEK_API_KEY") 
    perplexity_api_key: Optional[str] = Field(None, env="PERPLEXITY_API_KEY")
    mistralai_api_key: Optional[str] = Field(None, env="MISTRALAI_API_KEY")
    codestral_api_key: Optional[str] = Field(None, env="CODESTRAL_API_KEY")
    google_api_key: Optional[str] = Field(None, env="GOOGLE_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    elevenlabs_api_key: Optional[str] = Field(None, env="ELEVENLABS_API_KEY")
    serper_api_key: Optional[str] = Field(None, env="SERPER_API_KEY")
    
    # Application settings
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    def get_allowed_users_list(self) -> List[str]:
        """Parse allowed users string into list"""
        if isinstance(self.allowed_users, str):
            return [user.strip().lower() for user in self.allowed_users.split(',') if user.strip()]
        return []

# Global settings instance
_settings: Optional[SimpleSettings] = None

def get_settings() -> SimpleSettings:
    """Get the global settings instance"""
    global _settings
    if _settings is None:
        _settings = SimpleSettings()
    return _settings

# For backward compatibility
def validate_settings() -> SimpleSettings:
    """Validate and return settings"""
    return get_settings()

# Create settings instance
settings = get_settings()

# Legacy aliases for backward compatibility
Settings = SimpleSettings
