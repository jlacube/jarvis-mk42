# utils/exceptions.py
"""
Custom exception classes for Jarvis-MK42
"""

class JarvisError(Exception):
    """Base exception class for Jarvis-MK42"""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

class ConfigurationError(JarvisError):
    """Raised when there's a configuration issue"""
    pass

class AuthenticationError(JarvisError):
    """Raised when authentication fails"""
    pass

class AuthorizationError(JarvisError):
    """Raised when user is not authorized for an action"""
    pass

class ToolError(JarvisError):
    """Raised when a tool fails to execute"""
    pass

class AgentError(JarvisError):
    """Raised when an agent fails to process a request"""
    pass

class APIError(JarvisError):
    """Raised when an external API call fails"""
    def __init__(self, message: str, service: str, status_code: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.service = service
        self.status_code = status_code

class ValidationError(JarvisError):
    """Raised when input validation fails"""
    def __init__(self, message: str, field: str = None, value=None, **kwargs):
        super().__init__(message, **kwargs)
        self.field = field
        self.value = value

class DatabaseError(JarvisError):
    """Raised when database operations fail"""
    pass

class SessionError(JarvisError):
    """Raised when session management fails"""
    pass

class AudioProcessingError(JarvisError):
    """Raised when audio processing fails"""
    pass

class ImageProcessingError(JarvisError):
    """Raised when image processing fails"""
    pass

class VideoProcessingError(JarvisError):
    """Raised when video processing fails"""
    pass

# Aliases for backward compatibility and consistent naming
JarvisValidationError = ValidationError
JarvisAPIError = APIError  
JarvisToolError = ToolError
JarvisConfigurationError = ConfigurationError
JarvisDatabaseError = DatabaseError
