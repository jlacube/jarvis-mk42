"""
JARVIS-MK42 Security Module
===========================

This module provides comprehensive security capabilities including:
- Security audit framework with penetration testing prep
- API security hardening with rate limiting and DDoS protection
- Enhanced authentication with MFA and RBAC
- Data encryption at rest and in transit
"""

# Import security classes with graceful fallback
try:
    from .security_audit import SecurityAuditor
    SECURITY_AUDIT_AVAILABLE = True
except ImportError:
    SECURITY_AUDIT_AVAILABLE = False

try:
    from .api_security import APISecurityManager, RateLimitTracker
    API_SECURITY_AVAILABLE = True
except ImportError:
    API_SECURITY_AVAILABLE = False

try:
    from .enhanced_auth import EnhancedAuthSystem, User, Session
    ENHANCED_AUTH_AVAILABLE = True
except ImportError:
    ENHANCED_AUTH_AVAILABLE = False

try:
    from .data_encryption import DataEncryption, KeyManager
    DATA_ENCRYPTION_AVAILABLE = True
except ImportError:
    DATA_ENCRYPTION_AVAILABLE = False

__version__ = "1.0.0"
__author__ = "JARVIS-MK42"

def get_available_security_systems():
    """Get list of available security systems"""
    available = {}
    
    if SECURITY_AUDIT_AVAILABLE:
        available['security_audit'] = SecurityAuditor
    
    if API_SECURITY_AVAILABLE:
        available['api_security'] = APISecurityManager
    
    if ENHANCED_AUTH_AVAILABLE:
        available['enhanced_auth'] = EnhancedAuthSystem
    
    if DATA_ENCRYPTION_AVAILABLE:
        available['data_encryption'] = DataEncryption
    
    return available

def initialize_security_systems():
    """Initialize all available security systems"""
    available_systems = get_available_security_systems()
    initialized_systems = {}
    
    for system_name, system_class in available_systems.items():
        try:
            instance = system_class()
            initialized_systems[system_name] = instance
            print(f"✓ Security system initialized: {system_name}")
        except Exception as e:
            print(f"✗ Failed to initialize {system_name}: {e}")
    
    return initialized_systems

def get_security_status():
    """Get status of all security systems"""
    return {
        'security_audit_available': SECURITY_AUDIT_AVAILABLE,
        'api_security_available': API_SECURITY_AVAILABLE,
        'enhanced_auth_available': ENHANCED_AUTH_AVAILABLE,
        'data_encryption_available': DATA_ENCRYPTION_AVAILABLE,
        'total_available': sum([
            SECURITY_AUDIT_AVAILABLE,
            API_SECURITY_AVAILABLE,
            ENHANCED_AUTH_AVAILABLE,
            DATA_ENCRYPTION_AVAILABLE
        ])
    }

# Export all available classes
__all__ = []

if SECURITY_AUDIT_AVAILABLE:
    __all__.extend(['SecurityAuditor'])

if API_SECURITY_AVAILABLE:
    __all__.extend(['APISecurityManager', 'RateLimitTracker'])

if ENHANCED_AUTH_AVAILABLE:
    __all__.extend(['EnhancedAuthSystem', 'User', 'Session'])

if DATA_ENCRYPTION_AVAILABLE:
    __all__.extend(['DataEncryption', 'KeyManager'])

__all__.extend([
    'get_available_security_systems',
    'initialize_security_systems', 
    'get_security_status'
])
