# config.py - Legacy compatibility layer
# This file is kept for backward compatibility
# New code should use config.settings directly

from config.settings import get_settings

# Get settings instance
_settings = get_settings()

# Legacy constants for backward compatibility
SUPERVISOR_PROMPT_NAME = _settings.app.supervisor_prompt_name
JARVIS_NAME = _settings.app.jarvis_name
RECURSION_LIMIT = _settings.models.recursion_limit
MPV_INSTALLED = _settings.audio.mpv_installed

# Export settings for new code
settings = _settings
