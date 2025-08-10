# config/settings.py
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from pathlib import Path

class DatabaseSettings(BaseSettings):
    """Database configuration settings"""
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "allow"}
    
    url: str = Field("sqlite:///jarvis.db", env="DATABASE_URL")
    echo: bool = Field(False, env="DATABASE_ECHO")
    pool_size: int = Field(5, env="DATABASE_POOL_SIZE")
    max_overflow: int = Field(10, env="DATABASE_MAX_OVERFLOW")

class RedisSettings(BaseSettings):
    """Redis configuration settings"""
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "allow"}
    
    url: str = Field("redis://localhost:6379", env="REDIS_URL")
    password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    db: int = Field(0, env="REDIS_DB")
    max_connections: int = Field(10, env="REDIS_MAX_CONNECTIONS")

class ModelSettings(BaseSettings):
    """AI Model configuration settings"""
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "allow"}
    
    default_temperature: float = Field(0.0, env="MODEL_TEMPERATURE")
    default_max_tokens: int = Field(8192, env="MODEL_MAX_TOKENS")
    streaming: bool = Field(False, env="MODEL_STREAMING")
    recursion_limit: int = Field(250, env="RECURSION_LIMIT")

class APISettings(BaseSettings):
    """External API configuration settings"""
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "allow"}
    
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    google_api_key: Optional[str] = Field(None, env="GOOGLE_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    mistral_api_key: Optional[str] = Field(None, env="MISTRAL_API_KEY")
    elevenlabs_api_key: Optional[str] = Field(None, env="ELEVENLABS_API_KEY")
    serper_api_key: Optional[str] = Field(None, env="SERPER_API_KEY")
    perplexity_api_key: Optional[str] = Field(None, env="PERPLEXITY_API_KEY")

class AudioSettings(BaseSettings):
    """Audio processing configuration settings"""
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "allow"}
    
    mpv_installed: bool = Field(False, env="MPV_INSTALLED")
    default_language: str = Field("en", env="DEFAULT_LANGUAGE")
    audio_timeout: int = Field(30, env="AUDIO_TIMEOUT")

class SecuritySettings(BaseSettings):
    """Security and authentication settings"""
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "allow"}
    
    secret_key: str = Field("default-secret-key", env="SECRET_KEY")  # Make optional with default
    allowed_users: str = Field("admin", env="ALLOWED_USERS")  # Store as string, parse in property
    enforce_users: bool = Field(True, env="ENFORCE_USERS")
    session_timeout: int = Field(3600, env="SESSION_TIMEOUT")  # 1 hour
    max_login_attempts: int = Field(5, env="MAX_LOGIN_ATTEMPTS")
    
    @property
    def allowed_users_list(self) -> List[str]:
        """Get allowed users as a list"""
        if isinstance(self.allowed_users, str):
            return [user.strip().lower() for user in self.allowed_users.split(',') if user.strip()]
        return []

class LoggingSettings(BaseSettings):
    """Logging configuration settings"""
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "allow"}
    
    level: str = Field("INFO", env="LOG_LEVEL")
    format: str = Field("%(asctime)s - %(name)s - %(levelname)s - %(message)s", env="LOG_FORMAT")
    file_path: Optional[str] = Field("app.log", env="LOG_FILE_PATH")
    max_file_size: int = Field(10 * 1024 * 1024, env="LOG_MAX_FILE_SIZE")  # 10MB
    backup_count: int = Field(5, env="LOG_BACKUP_COUNT")

class ApplicationSettings(BaseSettings):
    """General application settings"""
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "allow"}
    
    debug: bool = Field(False, env="DEBUG")
    environment: str = Field("production", env="ENVIRONMENT")
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    jarvis_name: str = Field("Jarvis_MK42", env="JARVIS_NAME")
    supervisor_prompt_name: str = Field("supervisor", env="SUPERVISOR_PROMPT_NAME")

class Settings(BaseSettings):
    """Main settings class that combines all configuration sections"""
    model_config = {"extra": "allow", "env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False}
    
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    models: ModelSettings = ModelSettings()
    apis: APISettings = APISettings()
    audio: AudioSettings = AudioSettings()
    security: SecuritySettings = SecuritySettings()
    logging: LoggingSettings = LoggingSettings()
    app: ApplicationSettings = ApplicationSettings()

    def validate_required_apis(self) -> List[str]:
        """Validate that required API keys are present"""
        missing_keys = []
        
        # Check for at least one LLM provider
        llm_providers = [
            ("Google", self.apis.google_api_key),
            ("OpenAI", self.apis.openai_api_key),
            ("Anthropic", self.apis.anthropic_api_key),
            ("Mistral", self.apis.mistral_api_key)
        ]
        
        if not any(key for _, key in llm_providers if key):
            missing_keys.append("At least one LLM provider API key (GOOGLE_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, or MISTRAL_API_KEY)")
        
        # Check for search providers
        if not self.apis.serper_api_key:
            missing_keys.append("SERPER_API_KEY (for Google search functionality)")
            
        return missing_keys

    def get_user_password_hash(self, username: str) -> Optional[str]:
        """Get password hash for a specific user from environment variables"""
        return os.getenv(username.lower())

    @property
    def project_root(self) -> Path:
        """Get the project root directory"""
        return Path(__file__).parent.parent

    @property
    def prompts_dir(self) -> Path:
        """Get the prompts directory"""
        return self.project_root / "prompts"

    @property
    def tools_dir(self) -> Path:
        """Get the tools directory"""
        return self.project_root / "tools"

# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get the global settings instance"""
    return settings

def validate_settings():
    """Validate settings and raise errors for missing required configuration"""
    missing_apis = settings.validate_required_apis()
    
    if missing_apis:
        raise ValueError(f"Missing required API keys:\n" + "\n".join(f"- {key}" for key in missing_apis))
    
    # Validate secret key for security
    if not settings.security.secret_key or settings.security.secret_key == "changeme":
        raise ValueError("SECRET_KEY must be set to a secure random value")
    
    return True
