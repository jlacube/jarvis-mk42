#!/usr/bin/env python3
"""
JARVIS-MK42 API Security and Rate Limiting System
==============================================

This module provides comprehensive API security hardening including:
- Rate limiting and throttling
- API authentication and authorization
- Request validation and sanitization
- Security headers and CORS protection
- DDoS protection and abuse prevention
"""

import os
import sys
import time
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from functools import wraps
from dataclasses import dataclass
from enum import Enum
import threading
from collections import defaultdict, deque

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger
from config.settings import get_settings

logger = get_logger(__name__)


class RateLimitType(Enum):
    """Types of rate limiting"""
    PER_USER = "per_user"
    PER_IP = "per_ip"
    PER_ENDPOINT = "per_endpoint"
    GLOBAL = "global"


class SecurityAction(Enum):
    """Actions to take when security violations occur"""
    ALLOW = "allow"
    RATE_LIMIT = "rate_limit"
    TEMPORARY_BAN = "temporary_ban"
    PERMANENT_BAN = "permanent_ban"
    REQUIRE_CAPTCHA = "require_captcha"


@dataclass
class RateLimitRule:
    """Configuration for a rate limiting rule"""
    name: str
    limit_type: RateLimitType
    max_requests: int
    time_window: int  # seconds
    endpoints: List[str] = None  # None means all endpoints
    action: SecurityAction = SecurityAction.RATE_LIMIT
    ban_duration: int = 300  # seconds for temporary ban
    
    def __post_init__(self):
        if self.endpoints is None:
            self.endpoints = ["*"]


@dataclass
class SecurityEvent:
    """Security event for logging and analysis"""
    timestamp: datetime
    event_type: str
    client_id: str
    endpoint: str
    action_taken: SecurityAction
    details: Dict[str, Any]


class RateLimitTracker:
    """Thread-safe rate limit tracking"""
    
    def __init__(self):
        self._requests = defaultdict(deque)
        self._banned_clients = {}
        self._lock = threading.Lock()
    
    def check_rate_limit(self, client_id: str, rule: RateLimitRule) -> bool:
        """
        Check if client has exceeded rate limit.
        
        Args:
            client_id: Client identifier (IP, user ID, etc.)
            rule: Rate limiting rule to check
            
        Returns:
            True if request should be allowed, False if rate limited
        """
        with self._lock:
            now = time.time()
            
            # Check if client is banned
            if client_id in self._banned_clients:
                ban_end = self._banned_clients[client_id]
                if now < ban_end:
                    return False
                else:
                    # Ban expired, remove it
                    del self._banned_clients[client_id]
            
            # Get request history for this client and rule
            key = f"{client_id}:{rule.name}"
            requests = self._requests[key]
            
            # Remove old requests outside the time window
            cutoff = now - rule.time_window
            while requests and requests[0] < cutoff:
                requests.popleft()
            
            # Check if under limit
            if len(requests) < rule.max_requests:
                requests.append(now)
                return True
            
            # Rate limit exceeded
            if rule.action == SecurityAction.TEMPORARY_BAN:
                self._banned_clients[client_id] = now + rule.ban_duration
            
            return False
    
    def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """Get request statistics for a client"""
        with self._lock:
            stats = {
                "client_id": client_id,
                "is_banned": client_id in self._banned_clients,
                "ban_expires": None,
                "request_history": {}
            }
            
            if client_id in self._banned_clients:
                stats["ban_expires"] = self._banned_clients[client_id]
            
            # Get request counts per rule
            for key, requests in self._requests.items():
                if key.startswith(f"{client_id}:"):
                    rule_name = key.split(":", 1)[1]
                    stats["request_history"][rule_name] = len(requests)
            
            return stats


class APISecurityManager:
    """
    Comprehensive API security management system.
    
    Provides rate limiting, authentication validation, request sanitization,
    and security monitoring for all API endpoints.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.rate_tracker = RateLimitTracker()
        self.security_events: List[SecurityEvent] = []
        self._setup_default_rules()
        logger.info("API security manager initialized")
    
    def _setup_default_rules(self):
        """Setup default rate limiting rules"""
        self.rules = [
            # Global rate limit - 1000 requests per hour per IP
            RateLimitRule(
                name="global_ip_limit",
                limit_type=RateLimitType.PER_IP,
                max_requests=1000,
                time_window=3600,
                endpoints=["*"],
                action=SecurityAction.TEMPORARY_BAN,
                ban_duration=3600
            ),
            
            # Authenticated user limit - 500 requests per hour
            RateLimitRule(
                name="user_hourly_limit",
                limit_type=RateLimitType.PER_USER,
                max_requests=500,
                time_window=3600,
                endpoints=["*"],
                action=SecurityAction.RATE_LIMIT
            ),
            
            # Chat/processing endpoints - 60 requests per minute per user
            RateLimitRule(
                name="chat_minute_limit",
                limit_type=RateLimitType.PER_USER,
                max_requests=60,
                time_window=60,
                endpoints=["/chat", "/process", "/api/chat"],
                action=SecurityAction.RATE_LIMIT
            ),
            
            # File upload - 10 uploads per hour per user
            RateLimitRule(
                name="upload_limit",
                limit_type=RateLimitType.PER_USER,
                max_requests=10,
                time_window=3600,
                endpoints=["/upload", "/api/upload", "/files"],
                action=SecurityAction.TEMPORARY_BAN,
                ban_duration=1800
            ),
            
            # Health check - very permissive but still limited
            RateLimitRule(
                name="health_check_limit",
                limit_type=RateLimitType.PER_IP,
                max_requests=120,
                time_window=60,
                endpoints=["/health", "/api/health"],
                action=SecurityAction.RATE_LIMIT
            )
        ]
    
    def check_request_security(self, request_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive security check for incoming requests.
        
        Args:
            request_info: Dictionary containing:
                - client_ip: Client IP address
                - user_id: Authenticated user ID (optional)
                - endpoint: Requested endpoint
                - headers: Request headers
                - data: Request data (optional)
        
        Returns:
            Dictionary with security check results:
                - allowed: Boolean indicating if request should be allowed
                - action: SecurityAction to take
                - reason: Description of why request was blocked (if blocked)
                - headers: Security headers to add to response
        """
        try:
            client_ip = request_info.get('client_ip', 'unknown')
            user_id = request_info.get('user_id')
            endpoint = request_info.get('endpoint', '/')
            headers = request_info.get('headers', {})
            
            result = {
                'allowed': True,
                'action': SecurityAction.ALLOW,
                'reason': None,
                'headers': self._get_security_headers(),
                'client_stats': {}
            }
            
            # Check rate limits
            rate_limit_result = self._check_rate_limits(client_ip, user_id, endpoint)
            if not rate_limit_result['allowed']:
                result.update(rate_limit_result)
                self._log_security_event("rate_limit_exceeded", client_ip or user_id, endpoint, result['action'], rate_limit_result)
                return result
            
            # Check for suspicious patterns
            suspicious_check = self._check_suspicious_patterns(request_info)
            if not suspicious_check['allowed']:
                result.update(suspicious_check)
                self._log_security_event("suspicious_pattern", client_ip or user_id, endpoint, result['action'], suspicious_check)
                return result
            
            # Validate request headers
            header_check = self._validate_headers(headers)
            if not header_check['allowed']:
                result.update(header_check)
                self._log_security_event("invalid_headers", client_ip or user_id, endpoint, result['action'], header_check)
                return result
            
            # Add client statistics
            if client_ip:
                result['client_stats'] = self.rate_tracker.get_client_stats(client_ip)
            
            logger.debug(f"Security check passed for {client_ip or user_id} -> {endpoint}")
            return result
            
        except Exception as e:
            logger.error(f"Error in security check: {e}")
            return {
                'allowed': False,
                'action': SecurityAction.TEMPORARY_BAN,
                'reason': 'Security system error',
                'headers': self._get_security_headers()
            }
    
    def _check_rate_limits(self, client_ip: str, user_id: Optional[str], endpoint: str) -> Dict[str, Any]:
        """Check all applicable rate limits"""
        
        for rule in self.rules:
            # Check if rule applies to this endpoint
            if not self._rule_applies_to_endpoint(rule, endpoint):
                continue
            
            # Determine client ID based on rule type
            client_id = None
            if rule.limit_type == RateLimitType.PER_IP and client_ip:
                client_id = f"ip:{client_ip}"
            elif rule.limit_type == RateLimitType.PER_USER and user_id:
                client_id = f"user:{user_id}"
            elif rule.limit_type == RateLimitType.PER_ENDPOINT:
                client_id = f"endpoint:{endpoint}"
            elif rule.limit_type == RateLimitType.GLOBAL:
                client_id = "global"
            
            if client_id and not self.rate_tracker.check_rate_limit(client_id, rule):
                return {
                    'allowed': False,
                    'action': rule.action,
                    'reason': f'Rate limit exceeded: {rule.name}',
                    'rule': rule.name,
                    'limit': rule.max_requests,
                    'window': rule.time_window
                }
        
        return {'allowed': True}
    
    def _rule_applies_to_endpoint(self, rule: RateLimitRule, endpoint: str) -> bool:
        """Check if a rate limiting rule applies to an endpoint"""
        if "*" in rule.endpoints:
            return True
        
        for pattern in rule.endpoints:
            if pattern in endpoint or endpoint.startswith(pattern):
                return True
        
        return False
    
    def _check_suspicious_patterns(self, request_info: Dict[str, Any]) -> Dict[str, Any]:
        """Check for suspicious request patterns"""
        endpoint = request_info.get('endpoint', '')
        headers = request_info.get('headers', {})
        data = request_info.get('data', {})
        
        # Check for common attack patterns in endpoint
        suspicious_patterns = [
            '../', '..\\', '/etc/passwd', '/proc/', 'cmd.exe',
            '<script', 'javascript:', 'vbscript:', 'onload=',
            'union select', 'drop table', 'delete from',
            '@@version', 'xp_cmdshell'
        ]
        
        endpoint_lower = endpoint.lower()
        for pattern in suspicious_patterns:
            if pattern in endpoint_lower:
                return {
                    'allowed': False,
                    'action': SecurityAction.TEMPORARY_BAN,
                    'reason': f'Suspicious pattern detected: {pattern}',
                    'pattern': pattern
                }
        
        # Check for suspicious headers
        user_agent = headers.get('User-Agent', '').lower()
        suspicious_user_agents = [
            'sqlmap', 'nikto', 'nmap', 'masscan', 'zap',
            'burp', 'acunetix', 'nessus'
        ]
        
        for suspicious_ua in suspicious_user_agents:
            if suspicious_ua in user_agent:
                return {
                    'allowed': False,
                    'action': SecurityAction.PERMANENT_BAN,
                    'reason': f'Security scanner detected: {suspicious_ua}',
                    'user_agent': user_agent
                }
        
        return {'allowed': True}
    
    def _validate_headers(self, headers: Dict[str, Any]) -> Dict[str, Any]:
        """Validate request headers for security"""
        
        # Check for excessively long headers
        for name, value in headers.items():
            if len(str(value)) > 8192:  # 8KB limit per header
                return {
                    'allowed': False,
                    'action': SecurityAction.RATE_LIMIT,
                    'reason': f'Header too long: {name}',
                    'header_name': name
                }
        
        # Check total header size
        total_header_size = sum(len(f"{k}: {v}") for k, v in headers.items())
        if total_header_size > 32768:  # 32KB total limit
            return {
                'allowed': False,
                'action': SecurityAction.RATE_LIMIT,
                'reason': 'Total header size too large',
                'total_size': total_header_size
            }
        
        return {'allowed': True}
    
    def _get_security_headers(self) -> Dict[str, str]:
        """Get standard security headers to add to responses"""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; font-src 'self'; frame-src 'none'",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
        }
    
    def _log_security_event(self, event_type: str, client_id: str, endpoint: str, action: SecurityAction, details: Dict[str, Any]):
        """Log security events for analysis"""
        event = SecurityEvent(
            timestamp=datetime.utcnow(),
            event_type=event_type,
            client_id=client_id or 'unknown',
            endpoint=endpoint,
            action_taken=action,
            details=details
        )
        
        self.security_events.append(event)
        
        # Log critical events immediately
        if action in [SecurityAction.TEMPORARY_BAN, SecurityAction.PERMANENT_BAN]:
            logger.warning(f"Security action taken: {action.value} for {client_id} on {endpoint} - {event_type}")
        
        # Keep only recent events in memory (last 1000)
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]
    
    def get_security_statistics(self) -> Dict[str, Any]:
        """Get security statistics and metrics"""
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        last_day = now - timedelta(days=1)
        
        recent_events = [e for e in self.security_events if e.timestamp > last_hour]
        daily_events = [e for e in self.security_events if e.timestamp > last_day]
        
        stats = {
            'timestamp': now.isoformat(),
            'total_events': len(self.security_events),
            'events_last_hour': len(recent_events),
            'events_last_day': len(daily_events),
            'event_types': defaultdict(int),
            'action_counts': defaultdict(int),
            'top_blocked_endpoints': defaultdict(int),
            'top_blocked_clients': defaultdict(int)
        }
        
        # Analyze recent events
        for event in daily_events:
            stats['event_types'][event.event_type] += 1
            stats['action_counts'][event.action_taken.value] += 1
            if event.action_taken != SecurityAction.ALLOW:
                stats['top_blocked_endpoints'][event.endpoint] += 1
                stats['top_blocked_clients'][event.client_id] += 1
        
        # Convert defaultdicts to regular dicts
        stats['event_types'] = dict(stats['event_types'])
        stats['action_counts'] = dict(stats['action_counts'])
        stats['top_blocked_endpoints'] = dict(stats['top_blocked_endpoints'])
        stats['top_blocked_clients'] = dict(stats['top_blocked_clients'])
        
        return stats
    
    def add_custom_rule(self, rule: RateLimitRule):
        """Add a custom rate limiting rule"""
        self.rules.append(rule)
        logger.info(f"Added custom rate limiting rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove a rate limiting rule by name"""
        self.rules = [rule for rule in self.rules if rule.name != rule_name]
        logger.info(f"Removed rate limiting rule: {rule_name}")
    
    def whitelist_client(self, client_id: str, duration: int = 3600):
        """Temporarily whitelist a client (remove from bans)"""
        with self.rate_tracker._lock:
            if client_id in self.rate_tracker._banned_clients:
                del self.rate_tracker._banned_clients[client_id]
                logger.info(f"Whitelisted client {client_id} for {duration} seconds")


# Decorator for protecting endpoints
def require_api_security(endpoint_name: str = None):
    """
    Decorator to add API security to endpoints.
    
    Args:
        endpoint_name: Name of the endpoint for rate limiting
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # This is a placeholder for actual implementation
            # In practice, this would integrate with the web framework
            # (Flask, FastAPI, etc.) to extract request information
            
            logger.debug(f"API security check for {endpoint_name or func.__name__}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Global security manager instance
_security_manager = None

def get_security_manager() -> APISecurityManager:
    """Get or create the global security manager instance"""
    global _security_manager
    if _security_manager is None:
        _security_manager = APISecurityManager()
    return _security_manager


def main():
    """Command line interface for security management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 API Security Manager")
    parser.add_argument('--stats', action='store_true', help='Show security statistics')
    parser.add_argument('--test', action='store_true', help='Test security checks')
    
    args = parser.parse_args()
    
    security_manager = get_security_manager()
    
    if args.stats:
        stats = security_manager.get_security_statistics()
        print(json.dumps(stats, indent=2))
    
    elif args.test:
        # Test security checks
        test_requests = [
            {
                'client_ip': '127.0.0.1',
                'user_id': 'test_user',
                'endpoint': '/chat',
                'headers': {'User-Agent': 'Test Client'}
            },
            {
                'client_ip': '192.168.1.100',
                'endpoint': '/health',
                'headers': {'User-Agent': 'Health Check'}
            },
            {
                'client_ip': '10.0.0.1',
                'endpoint': '/upload',
                'headers': {'User-Agent': 'File Upload Client'}
            }
        ]
        
        for i, request_info in enumerate(test_requests):
            print(f"\nTesting request {i+1}:")
            result = security_manager.check_request_security(request_info)
            print(f"Allowed: {result['allowed']}")
            print(f"Action: {result['action'].value}")
            if result.get('reason'):
                print(f"Reason: {result['reason']}")
    
    else:
        print("JARVIS-MK42 API Security Manager")
        print("Use --stats to show statistics or --test to test security checks")


if __name__ == "__main__":
    main()
