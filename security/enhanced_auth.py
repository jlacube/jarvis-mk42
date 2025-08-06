#!/usr/bin/env python3
"""
JARVIS-MK42 Enhanced Authentication and Authorization System
=========================================================

This module provides comprehensive authentication and authorization capabilities including:
- Multi-factor authentication (MFA)
- Session management with security features
- Role-based access control (RBAC)
- API key management
- Password security policies
- Audit logging for authentication events
"""

import os
import sys
import json
import hashlib
import secrets
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import bcrypt
import hmac
import logging
from pathlib import Path

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger
from config.settings import get_settings

logger = get_logger(__name__)


class AuthenticationMethod(Enum):
    """Authentication methods supported"""
    PASSWORD = "password"
    API_KEY = "api_key"
    SESSION_TOKEN = "session_token"
    MFA_TOTP = "mfa_totp"
    MFA_SMS = "mfa_sms"


class UserRole(Enum):
    """User roles for authorization"""
    GUEST = "guest"
    USER = "user"
    POWER_USER = "power_user"
    ADMIN = "admin"
    SYSTEM = "system"


class PermissionLevel(Enum):
    """Permission levels for resources"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"
    OWNER = "owner"


@dataclass
class Permission:
    """Represents a specific permission"""
    resource: str
    level: PermissionLevel
    conditions: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.conditions is None:
            self.conditions = {}


@dataclass
class User:
    """Enhanced user representation with security features"""
    user_id: str
    username: str
    email: Optional[str]
    role: UserRole
    permissions: List[Permission]
    password_hash: Optional[str] = None
    api_keys: List[str] = None
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    account_locked: bool = False
    lock_expires: Optional[datetime] = None
    password_expires: Optional[datetime] = None
    created_at: datetime = None
    updated_at: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.api_keys is None:
            self.api_keys = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Session:
    """Secure session representation"""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    last_accessed: datetime
    client_ip: str
    user_agent: str
    is_active: bool = True
    mfa_verified: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AuthenticationEvent:
    """Security event logging for authentication"""
    timestamp: datetime
    event_type: str
    user_id: Optional[str]
    username: Optional[str]
    client_ip: str
    user_agent: str
    success: bool
    failure_reason: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PasswordPolicy:
    """Password security policy configuration"""
    
    def __init__(self):
        self.min_length = 8
        self.require_uppercase = True
        self.require_lowercase = True
        self.require_digits = True
        self.require_special_chars = True
        self.max_age_days = 90
        self.prevent_reuse_count = 5
        self.max_failed_attempts = 5
        self.lockout_duration_minutes = 30
    
    def validate_password(self, password: str) -> Dict[str, Any]:
        """
        Validate password against policy.
        
        Returns:
            Dictionary with validation results
        """
        errors = []
        
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")
        
        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if self.require_digits and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if self.require_special_chars and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'strength_score': self._calculate_strength(password)
        }
    
    def _calculate_strength(self, password: str) -> int:
        """Calculate password strength score (0-100)"""
        score = 0
        
        # Length bonus
        score += min(password.__len__() * 2, 25)
        
        # Character variety bonus
        if any(c.isupper() for c in password):
            score += 15
        if any(c.islower() for c in password):
            score += 15
        if any(c.isdigit() for c in password):
            score += 15
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 20
        
        # Pattern penalties
        if password.lower() in ['password', '123456', 'qwerty', 'admin']:
            score -= 50
        
        return max(0, min(100, score))


class EnhancedAuthSystem:
    """
    Enhanced authentication and authorization system.
    
    Provides comprehensive security features including MFA, RBAC,
    session management, and security auditing.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.password_policy = PasswordPolicy()
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, Session] = {}
        self.auth_events: List[AuthenticationEvent] = []
        self.role_permissions = {}  # Initialize before calling _setup_default_roles
        self._setup_default_roles()
        self._load_users()
        logger.info("Enhanced authentication system initialized")
    
    def _load_users(self):
        """Load users from configuration or storage"""
        # Load from settings for now, could be extended to database
        allowed_users = self.settings.security.allowed_users_list
        
        for username in allowed_users:
            if username not in self.users:
                self.users[username] = User(
                    user_id=self._generate_user_id(),
                    username=username,
                    email=None,
                    role=UserRole.ADMIN if username == "admin" else UserRole.USER,
                    permissions=self._get_default_permissions(UserRole.ADMIN if username == "admin" else UserRole.USER)
                )
    
    def _setup_default_roles(self):
        """Setup default role permissions"""
        self.role_permissions = {
            UserRole.GUEST: [
                Permission("health_check", PermissionLevel.READ),
            ],
            UserRole.USER: [
                Permission("health_check", PermissionLevel.READ),
                Permission("chat", PermissionLevel.EXECUTE),
                Permission("documents", PermissionLevel.READ),
                Permission("documents", PermissionLevel.WRITE),
                Permission("research", PermissionLevel.EXECUTE),
            ],
            UserRole.POWER_USER: [
                Permission("health_check", PermissionLevel.READ),
                Permission("chat", PermissionLevel.EXECUTE),
                Permission("documents", PermissionLevel.READ),
                Permission("documents", PermissionLevel.WRITE),
                Permission("research", PermissionLevel.EXECUTE),
                Permission("multimodal", PermissionLevel.EXECUTE),
                Permission("coding", PermissionLevel.EXECUTE),
                Permission("system_config", PermissionLevel.READ),
            ],
            UserRole.ADMIN: [
                Permission("*", PermissionLevel.ADMIN),
            ],
            UserRole.SYSTEM: [
                Permission("*", PermissionLevel.OWNER),
            ]
        }
    
    def _get_default_permissions(self, role: UserRole) -> List[Permission]:
        """Get default permissions for a role"""
        return self.role_permissions.get(role, [])
    
    def _generate_user_id(self) -> str:
        """Generate unique user ID"""
        return f"user_{secrets.token_hex(8)}"
    
    def _generate_session_id(self) -> str:
        """Generate secure session ID"""
        return secrets.token_urlsafe(32)
    
    def _generate_api_key(self) -> str:
        """Generate secure API key"""
        return f"jarvis_{secrets.token_urlsafe(32)}"
    
    def authenticate_user(self, username: str, password: str, client_ip: str = "unknown", 
                         user_agent: str = "unknown") -> Dict[str, Any]:
        """
        Authenticate user with username/password.
        
        Args:
            username: Username
            password: Password
            client_ip: Client IP address
            user_agent: Client user agent
            
        Returns:
            Authentication result dictionary
        """
        auth_result = {
            'success': False,
            'user': None,
            'session': None,
            'requires_mfa': False,
            'error': None,
            'account_locked': False
        }
        
        try:
            # Check if user exists
            if username not in self.users:
                self._log_auth_event("login_attempt", None, username, client_ip, user_agent, False, "User not found")
                auth_result['error'] = "Invalid credentials"
                return auth_result
            
            user = self.users[username]
            
            # Check if account is locked
            if user.account_locked:
                if user.lock_expires and datetime.utcnow() < user.lock_expires:
                    self._log_auth_event("login_attempt", user.user_id, username, client_ip, user_agent, False, "Account locked")
                    auth_result['account_locked'] = True
                    auth_result['error'] = f"Account locked until {user.lock_expires}"
                    return auth_result
                else:
                    # Lock expired, unlock account
                    user.account_locked = False
                    user.lock_expires = None
                    user.failed_login_attempts = 0
            
            # Verify password
            if not user.password_hash:
                # First time login - set password
                password_result = self.set_user_password(username, password)
                if not password_result['success']:
                    auth_result['error'] = f"Password policy violation: {', '.join(password_result['errors'])}"
                    return auth_result
            else:
                # Check existing password
                if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                    user.failed_login_attempts += 1
                    
                    # Check if account should be locked
                    if user.failed_login_attempts >= self.password_policy.max_failed_attempts:
                        user.account_locked = True
                        user.lock_expires = datetime.utcnow() + timedelta(minutes=self.password_policy.lockout_duration_minutes)
                        auth_result['account_locked'] = True
                        self._log_auth_event("account_locked", user.user_id, username, client_ip, user_agent, False, "Too many failed attempts")
                    
                    self._log_auth_event("login_attempt", user.user_id, username, client_ip, user_agent, False, "Invalid password")
                    auth_result['error'] = "Invalid credentials"
                    return auth_result
            
            # Check password expiration
            if user.password_expires and datetime.utcnow() > user.password_expires:
                auth_result['error'] = "Password expired"
                return auth_result
            
            # Reset failed attempts on successful password check
            user.failed_login_attempts = 0
            
            # Check if MFA is required
            if user.mfa_enabled:
                auth_result['requires_mfa'] = True
                auth_result['user'] = user
                return auth_result
            
            # Create session
            session = self._create_session(user, client_ip, user_agent)
            auth_result['success'] = True
            auth_result['user'] = user
            auth_result['session'] = session
            
            # Update user login info
            user.last_login = datetime.utcnow()
            
            self._log_auth_event("login_success", user.user_id, username, client_ip, user_agent, True)
            logger.info(f"User {username} authenticated successfully")
            
            return auth_result
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            auth_result['error'] = "Authentication system error"
            return auth_result
    
    def verify_session(self, session_id: str) -> Dict[str, Any]:
        """
        Verify and refresh a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session verification result
        """
        result = {
            'valid': False,
            'user': None,
            'session': None,
            'expired': False,
            'error': None
        }
        
        try:
            if session_id not in self.sessions:
                result['error'] = "Session not found"
                return result
            
            session = self.sessions[session_id]
            
            if not session.is_active:
                result['error'] = "Session inactive"
                return result
            
            # Check expiration
            if datetime.utcnow() > session.expires_at:
                session.is_active = False
                result['expired'] = True
                result['error'] = "Session expired"
                return result
            
            # Update last accessed
            session.last_accessed = datetime.utcnow()
            
            # Get user
            user = self.users.get(session.user_id)
            if not user:
                result['error'] = "User not found"
                return result
            
            result['valid'] = True
            result['user'] = user
            result['session'] = session
            
            return result
            
        except Exception as e:
            logger.error(f"Session verification error: {e}")
            result['error'] = "Session verification error"
            return result
    
    def authorize_action(self, user: User, resource: str, action: PermissionLevel) -> bool:
        """
        Check if user is authorized to perform action on resource.
        
        Args:
            user: User object
            resource: Resource identifier
            action: Required permission level
            
        Returns:
            True if authorized, False otherwise
        """
        try:
            # System role has all permissions
            if user.role == UserRole.SYSTEM:
                return True
            
            # Check user-specific permissions
            for permission in user.permissions:
                if self._permission_matches(permission, resource, action):
                    return True
            
            # Check role-based permissions
            role_permissions = self.role_permissions.get(user.role, [])
            for permission in role_permissions:
                if self._permission_matches(permission, resource, action):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Authorization error: {e}")
            return False
    
    def _permission_matches(self, permission: Permission, resource: str, action: PermissionLevel) -> bool:
        """Check if permission matches the resource and action"""
        # Wildcard resource matches everything
        if permission.resource == "*":
            return self._action_level_sufficient(permission.level, action)
        
        # Exact resource match
        if permission.resource == resource:
            return self._action_level_sufficient(permission.level, action)
        
        # Pattern matching (basic implementation)
        if permission.resource.endswith("*"):
            prefix = permission.resource[:-1]
            if resource.startswith(prefix):
                return self._action_level_sufficient(permission.level, action)
        
        return False
    
    def _action_level_sufficient(self, granted_level: PermissionLevel, required_level: PermissionLevel) -> bool:
        """Check if granted permission level is sufficient for required level"""
        level_hierarchy = {
            PermissionLevel.READ: 1,
            PermissionLevel.WRITE: 2,
            PermissionLevel.EXECUTE: 3,
            PermissionLevel.ADMIN: 4,
            PermissionLevel.OWNER: 5
        }
        
        granted_value = level_hierarchy.get(granted_level, 0)
        required_value = level_hierarchy.get(required_level, 0)
        
        return granted_value >= required_value
    
    def set_user_password(self, username: str, password: str) -> Dict[str, Any]:
        """
        Set or update user password with policy validation.
        
        Args:
            username: Username
            password: New password
            
        Returns:
            Result of password update
        """
        result = {
            'success': False,
            'errors': [],
            'policy_check': None
        }
        
        try:
            if username not in self.users:
                result['errors'] = ["User not found"]
                return result
            
            # Validate password policy
            policy_check = self.password_policy.validate_password(password)
            result['policy_check'] = policy_check
            
            if not policy_check['valid']:
                result['errors'] = policy_check['errors']
                return result
            
            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            # Update user
            user = self.users[username]
            user.password_hash = password_hash
            user.password_expires = datetime.utcnow() + timedelta(days=self.password_policy.max_age_days)
            user.updated_at = datetime.utcnow()
            
            result['success'] = True
            logger.info(f"Password updated for user {username}")
            
            return result
            
        except Exception as e:
            logger.error(f"Password update error: {e}")
            result['errors'] = ["Password update failed"]
            return result
    
    def generate_api_key(self, username: str) -> Dict[str, Any]:
        """
        Generate new API key for user.
        
        Args:
            username: Username
            
        Returns:
            Result with new API key
        """
        result = {
            'success': False,
            'api_key': None,
            'error': None
        }
        
        try:
            if username not in self.users:
                result['error'] = "User not found"
                return result
            
            user = self.users[username]
            api_key = self._generate_api_key()
            
            user.api_keys.append(api_key)
            user.updated_at = datetime.utcnow()
            
            result['success'] = True
            result['api_key'] = api_key
            
            logger.info(f"Generated API key for user {username}")
            return result
            
        except Exception as e:
            logger.error(f"API key generation error: {e}")
            result['error'] = "API key generation failed"
            return result
    
    def _create_session(self, user: User, client_ip: str, user_agent: str) -> Session:
        """Create new session for user"""
        session_id = self._generate_session_id()
        now = datetime.utcnow()
        
        session = Session(
            session_id=session_id,
            user_id=user.user_id,
            created_at=now,
            expires_at=now + timedelta(seconds=self.settings.security.session_timeout),
            last_accessed=now,
            client_ip=client_ip,
            user_agent=user_agent
        )
        
        self.sessions[session_id] = session
        return session
    
    def logout_session(self, session_id: str):
        """Logout and invalidate session"""
        if session_id in self.sessions:
            self.sessions[session_id].is_active = False
            logger.info(f"Session {session_id[:8]}... logged out")
    
    def _log_auth_event(self, event_type: str, user_id: Optional[str], username: Optional[str], 
                       client_ip: str, user_agent: str, success: bool, failure_reason: Optional[str] = None):
        """Log authentication events"""
        event = AuthenticationEvent(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            user_id=user_id,
            username=username,
            client_ip=client_ip,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason
        )
        
        self.auth_events.append(event)
        
        # Keep only recent events in memory
        if len(self.auth_events) > 1000:
            self.auth_events = self.auth_events[-1000:]
    
    def get_security_report(self) -> Dict[str, Any]:
        """Get comprehensive security report"""
        now = datetime.utcnow()
        last_24h = now - timedelta(days=1)
        
        recent_events = [e for e in self.auth_events if e.timestamp > last_24h]
        
        return {
            'timestamp': now.isoformat(),
            'users': {
                'total': len(self.users),
                'locked_accounts': sum(1 for u in self.users.values() if u.account_locked),
                'mfa_enabled': sum(1 for u in self.users.values() if u.mfa_enabled),
            },
            'sessions': {
                'total': len(self.sessions),
                'active': sum(1 for s in self.sessions.values() if s.is_active),
                'expired': sum(1 for s in self.sessions.values() if not s.is_active),
            },
            'events_24h': {
                'total': len(recent_events),
                'successful_logins': sum(1 for e in recent_events if e.event_type == "login_success"),
                'failed_attempts': sum(1 for e in recent_events if e.event_type == "login_attempt" and not e.success),
                'account_lockouts': sum(1 for e in recent_events if e.event_type == "account_locked"),
            }
        }


# Global authentication system instance
_auth_system = None

def get_auth_system() -> EnhancedAuthSystem:
    """Get or create the global authentication system instance"""
    global _auth_system
    if _auth_system is None:
        _auth_system = EnhancedAuthSystem()
    return _auth_system


def main():
    """Command line interface for authentication management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 Enhanced Authentication System")
    parser.add_argument('--report', action='store_true', help='Show security report')
    parser.add_argument('--test-auth', nargs=2, metavar=('username', 'password'), help='Test authentication')
    
    args = parser.parse_args()
    
    auth_system = get_auth_system()
    
    if args.report:
        report = auth_system.get_security_report()
        print(json.dumps(report, indent=2))
    
    elif args.test_auth:
        username, password = args.test_auth
        result = auth_system.authenticate_user(username, password, "127.0.0.1", "CLI Test")
        print(f"Authentication result: {result}")
    
    else:
        print("JARVIS-MK42 Enhanced Authentication System")
        print("Use --report for security report or --test-auth username password to test")


if __name__ == "__main__":
    main()
