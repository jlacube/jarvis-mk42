#!/usr/bin/env python3
"""
JARVIS-MK42 Production Security Audit Framework
============================================

This module provides comprehensive security auditing capabilities for production deployment,
including penetration testing preparation, vulnerability assessment, and security validation.
"""

import os
import sys
import json
import logging
import hashlib
import secrets
import ssl
import socket
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger
from config.settings import get_settings

logger = get_logger(__name__)


class SecurityRiskLevel(Enum):
    """Security risk severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SecurityCheckType(Enum):
    """Types of security checks"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    ENCRYPTION = "encryption"
    INPUT_VALIDATION = "input_validation"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    FILE_SYSTEM = "file_system"
    API_SECURITY = "api_security"
    DEPENDENCIES = "dependencies"


@dataclass
class SecurityFinding:
    """Represents a security audit finding"""
    check_type: SecurityCheckType
    risk_level: SecurityRiskLevel
    title: str
    description: str
    impact: str
    recommendation: str
    affected_components: List[str]
    cve_references: List[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.cve_references is None:
            self.cve_references = []


@dataclass
class SecurityAuditReport:
    """Complete security audit report"""
    audit_id: str
    timestamp: datetime
    findings: List[SecurityFinding]
    risk_summary: Dict[str, int]
    recommendations: List[str]
    compliance_status: Dict[str, bool]
    next_audit_date: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization"""
        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp.isoformat(),
            "findings": [asdict(finding) for finding in self.findings],
            "risk_summary": self.risk_summary,
            "recommendations": self.recommendations,
            "compliance_status": self.compliance_status,
            "next_audit_date": self.next_audit_date.isoformat()
        }


class SecurityAuditor:
    """
    Comprehensive security auditing system for JARVIS-MK42.
    
    Provides automated security checks, vulnerability assessment,
    and penetration testing preparation capabilities.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.findings: List[SecurityFinding] = []
        self.project_root = Path(project_root)
        logger.info("Security auditor initialized")
    
    def run_full_audit(self) -> SecurityAuditReport:
        """
        Execute comprehensive security audit.
        
        Returns:
            SecurityAuditReport: Complete audit results
        """
        logger.info("Starting comprehensive security audit")
        self.findings = []
        
        try:
            # Run all security checks
            self._check_authentication_security()
            self._check_authorization_security()
            self._check_encryption_configuration()
            self._check_input_validation()
            self._check_configuration_security()
            self._check_network_security()
            self._check_file_system_security()
            self._check_api_security()
            self._check_dependencies_security()
            
            # Generate report
            report = self._generate_report()
            
            # Save audit report
            self._save_audit_report(report)
            
            logger.info(f"Security audit completed with {len(self.findings)} findings")
            return report
            
        except Exception as e:
            logger.error(f"Security audit failed: {e}")
            raise
    
    def _check_authentication_security(self):
        """Check authentication mechanism security"""
        logger.debug("Checking authentication security")
        
        # Check secret key strength
        secret_key = self.settings.security.secret_key
        if secret_key == "default-secret-key":
            self.findings.append(SecurityFinding(
                check_type=SecurityCheckType.AUTHENTICATION,
                risk_level=SecurityRiskLevel.CRITICAL,
                title="Default Secret Key in Use",
                description="Application is using the default secret key instead of a secure random key",
                impact="Attackers can forge authentication tokens and session cookies",
                recommendation="Generate a strong random secret key using secrets.token_urlsafe()",
                affected_components=["authentication", "session_management"]
            ))
        elif len(secret_key) < 32:
            self.findings.append(SecurityFinding(
                check_type=SecurityCheckType.AUTHENTICATION,
                risk_level=SecurityRiskLevel.HIGH,
                title="Weak Secret Key",
                description=f"Secret key is only {len(secret_key)} characters, should be at least 32",
                impact="Reduced security against brute force attacks on authentication tokens",
                recommendation="Use a secret key of at least 32 characters",
                affected_components=["authentication", "session_management"]
            ))
        
        # Check session timeout configuration
        session_timeout = self.settings.security.session_timeout
        if session_timeout > 86400:  # 24 hours
            self.findings.append(SecurityFinding(
                check_type=SecurityCheckType.AUTHENTICATION,
                risk_level=SecurityRiskLevel.MEDIUM,
                title="Long Session Timeout",
                description=f"Session timeout is {session_timeout} seconds ({session_timeout/3600:.1f} hours)",
                impact="Increased risk of session hijacking and unauthorized access",
                recommendation="Consider reducing session timeout to 1-8 hours maximum",
                affected_components=["session_management"]
            ))
    
    def _check_authorization_security(self):
        """Check authorization and access control security"""
        logger.debug("Checking authorization security")
        
        # Check user enforcement
        if not self.settings.security.enforce_users:
            self.findings.append(SecurityFinding(
                check_type=SecurityCheckType.AUTHORIZATION,
                risk_level=SecurityRiskLevel.HIGH,
                title="User Enforcement Disabled",
                description="User authentication enforcement is disabled",
                impact="Anyone can access the system without authentication",
                recommendation="Enable user enforcement in production environments",
                affected_components=["authentication", "authorization"]
            ))
        
        # Check allowed users configuration
        allowed_users = self.settings.security.allowed_users_list
        if len(allowed_users) == 1 and "admin" in allowed_users:
            self.findings.append(SecurityFinding(
                check_type=SecurityCheckType.AUTHORIZATION,
                risk_level=SecurityRiskLevel.MEDIUM,
                title="Default Admin User",
                description="Only default 'admin' user is configured",
                impact="Predictable username increases attack surface",
                recommendation="Configure specific usernames and remove default admin account",
                affected_components=["user_management"]
            ))
    
    def _check_encryption_configuration(self):
        """Check encryption settings and implementation"""
        logger.debug("Checking encryption configuration")
        
        # Check database URL for encryption
        db_url = self.settings.database.url
        if db_url.startswith("postgresql://"):
            self.findings.append(SecurityFinding(
                check_type=SecurityCheckType.ENCRYPTION,
                risk_level=SecurityRiskLevel.HIGH,
                title="Unencrypted Database Connection",
                description="Database connection is not using SSL/TLS encryption",
                impact="Database traffic can be intercepted and credentials stolen",
                recommendation="Use postgresql+psycopg2:// with sslmode=require parameter",
                affected_components=["database"]
            ))
        
        # Check for API key exposure in environment
        api_keys = [
            ("OPENAI_API_KEY", self.settings.api.openai_api_key),
            ("GOOGLE_API_KEY", self.settings.api.google_api_key),
            ("ANTHROPIC_API_KEY", self.settings.api.anthropic_api_key),
        ]
        
        for key_name, key_value in api_keys:
            if key_value and len(key_value) < 20:
                self.findings.append(SecurityFinding(
                    check_type=SecurityCheckType.ENCRYPTION,
                    risk_level=SecurityRiskLevel.MEDIUM,
                    title=f"Potentially Weak {key_name}",
                    description=f"{key_name} appears to be unusually short",
                    impact="May indicate test/demo key in production",
                    recommendation="Verify API key is production-grade and properly secured",
                    affected_components=["api_keys"]
                ))
    
    def _check_input_validation(self):
        """Check input validation implementation"""
        logger.debug("Checking input validation")
        
        # Check if file tools have proper validation
        try:
            from tools.file_tools import DEFAULT_EXCLUDED_EXTENSIONS
            if len(DEFAULT_EXCLUDED_EXTENSIONS) < 5:
                self.findings.append(SecurityFinding(
                    check_type=SecurityCheckType.INPUT_VALIDATION,
                    risk_level=SecurityRiskLevel.MEDIUM,
                    title="Limited File Extension Filtering",
                    description="File extension filtering may not be comprehensive",
                    impact="Potential for malicious file uploads",
                    recommendation="Review and expand excluded file extensions list",
                    affected_components=["file_tools"]
                ))
        except ImportError:
            self.findings.append(SecurityFinding(
                check_type=SecurityCheckType.INPUT_VALIDATION,
                risk_level=SecurityRiskLevel.LOW,
                title="File Tools Not Available",
                description="Cannot verify file validation implementation",
                impact="Unknown input validation status",
                recommendation="Ensure file tools are properly installed",
                affected_components=["file_tools"]
            ))
    
    def _check_configuration_security(self):
        """Check configuration security"""
        logger.debug("Checking configuration security")
        
        # Check for debug mode in production
        try:
            import chainlit as cl
            # This is a placeholder - in real implementation would check debug flags
            pass
        except ImportError:
            pass
        
        # Check environment variable security
        env_vars_to_check = [
            "SECRET_KEY", "DATABASE_URL", "OPENAI_API_KEY", 
            "GOOGLE_API_KEY", "REDIS_PASSWORD"
        ]
        
        missing_env_vars = []
        for var in env_vars_to_check:
            if not os.environ.get(var):
                missing_env_vars.append(var)
        
        if missing_env_vars:
            self.findings.append(SecurityFinding(
                check_type=SecurityCheckType.CONFIGURATION,
                risk_level=SecurityRiskLevel.MEDIUM,
                title="Missing Environment Variables",
                description=f"Environment variables not set: {', '.join(missing_env_vars)}",
                impact="May be using insecure defaults or cause application errors",
                recommendation="Set all required environment variables for production",
                affected_components=["configuration"]
            ))
    
    def _check_network_security(self):
        """Check network security configuration"""
        logger.debug("Checking network security")
        
        # Check if running on default ports
        # This is a placeholder for actual port checking
        self.findings.append(SecurityFinding(
            check_type=SecurityCheckType.NETWORK,
            risk_level=SecurityRiskLevel.INFO,
            title="Network Security Review Needed",
            description="Manual review of network configuration recommended",
            impact="Potential network vulnerabilities",
            recommendation="Review firewall rules, port configurations, and network segmentation",
            affected_components=["network"]
        ))
    
    def _check_file_system_security(self):
        """Check file system security"""
        logger.debug("Checking file system security")
        
        # Check file permissions on sensitive files
        sensitive_files = [
            ".env",
            "config/settings.py",
            "users.py"
        ]
        
        for file_path in sensitive_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    stat_info = full_path.stat()
                    # Check if file is world-readable (on Unix-like systems)
                    if hasattr(stat_info, 'st_mode') and (stat_info.st_mode & 0o004):
                        self.findings.append(SecurityFinding(
                            check_type=SecurityCheckType.FILE_SYSTEM,
                            risk_level=SecurityRiskLevel.MEDIUM,
                            title=f"World-readable Sensitive File: {file_path}",
                            description=f"File {file_path} is readable by all users",
                            impact="Sensitive configuration may be exposed",
                            recommendation="Restrict file permissions to owner only (chmod 600)",
                            affected_components=["file_system"]
                        ))
                except Exception as e:
                    logger.debug(f"Could not check permissions for {file_path}: {e}")
    
    def _check_api_security(self):
        """Check API security implementation"""
        logger.debug("Checking API security")
        
        # This would check for rate limiting, CORS, etc.
        # Placeholder for actual API security checks
        self.findings.append(SecurityFinding(
            check_type=SecurityCheckType.API_SECURITY,
            risk_level=SecurityRiskLevel.INFO,
            title="API Security Configuration Review",
            description="API security configuration should be reviewed",
            impact="Potential API vulnerabilities",
            recommendation="Implement rate limiting, CORS headers, and API authentication",
            affected_components=["api"]
        ))
    
    def _check_dependencies_security(self):
        """Check dependency security"""
        logger.debug("Checking dependency security")
        
        # Check for requirements.txt
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            try:
                with open(requirements_file, 'r') as f:
                    requirements = f.read()
                
                # Check for pinned versions
                unpinned_count = requirements.count(">=")
                if unpinned_count > 0:
                    self.findings.append(SecurityFinding(
                        check_type=SecurityCheckType.DEPENDENCIES,
                        risk_level=SecurityRiskLevel.MEDIUM,
                        title="Unpinned Dependencies",
                        description=f"Found {unpinned_count} dependencies without exact version pins",
                        impact="May install vulnerable versions of dependencies",
                        recommendation="Pin all dependencies to specific versions",
                        affected_components=["dependencies"]
                    ))
                    
            except Exception as e:
                logger.debug(f"Could not read requirements.txt: {e}")
        else:
            self.findings.append(SecurityFinding(
                check_type=SecurityCheckType.DEPENDENCIES,
                risk_level=SecurityRiskLevel.LOW,
                title="No Requirements File",
                description="No requirements.txt file found",
                impact="Dependency versions not tracked",
                recommendation="Create requirements.txt with pinned versions",
                affected_components=["dependencies"]
            ))
    
    def _generate_report(self) -> SecurityAuditReport:
        """Generate comprehensive security audit report"""
        
        # Calculate risk summary
        risk_summary = {level.value: 0 for level in SecurityRiskLevel}
        for finding in self.findings:
            risk_summary[finding.risk_level.value] += 1
        
        # Generate recommendations
        recommendations = []
        if risk_summary['critical'] > 0:
            recommendations.append("Address critical security issues immediately before production deployment")
        if risk_summary['high'] > 0:
            recommendations.append("Resolve high-risk security issues within 24 hours")
        if risk_summary['medium'] > 0:
            recommendations.append("Plan to address medium-risk issues within one week")
        
        # Check compliance status
        compliance_status = {
            "authentication_configured": risk_summary['critical'] == 0,
            "encryption_enabled": not any(f.check_type == SecurityCheckType.ENCRYPTION and f.risk_level in [SecurityRiskLevel.CRITICAL, SecurityRiskLevel.HIGH] for f in self.findings),
            "input_validation_present": not any(f.check_type == SecurityCheckType.INPUT_VALIDATION and f.risk_level == SecurityRiskLevel.CRITICAL for f in self.findings),
            "secure_configuration": not any(f.check_type == SecurityCheckType.CONFIGURATION and f.risk_level == SecurityRiskLevel.CRITICAL for f in self.findings)
        }
        
        return SecurityAuditReport(
            audit_id=f"audit_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.utcnow(),
            findings=self.findings,
            risk_summary=risk_summary,
            recommendations=recommendations,
            compliance_status=compliance_status,
            next_audit_date=datetime.utcnow() + timedelta(days=30)
        )
    
    def _save_audit_report(self, report: SecurityAuditReport):
        """Save audit report to file"""
        try:
            # Create security reports directory
            reports_dir = self.project_root / "security" / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            # Save report
            report_file = reports_dir / f"security_audit_{report.audit_id}.json"
            with open(report_file, 'w') as f:
                json.dump(report.to_dict(), f, indent=2, default=str)
            
            logger.info(f"Security audit report saved to {report_file}")
            
        except Exception as e:
            logger.error(f"Failed to save audit report: {e}")
    
    def run_penetration_test_prep(self) -> Dict[str, Any]:
        """
        Prepare system for penetration testing by identifying attack surfaces.
        
        Returns:
            Dictionary with penetration testing preparation information
        """
        logger.info("Running penetration testing preparation")
        
        prep_info = {
            "timestamp": datetime.utcnow().isoformat(),
            "attack_surfaces": [],
            "test_accounts": [],
            "network_endpoints": [],
            "security_controls": []
        }
        
        # Identify attack surfaces
        prep_info["attack_surfaces"] = [
            {
                "component": "Web Interface",
                "description": "Chainlit web interface",
                "potential_attacks": ["XSS", "CSRF", "Session hijacking"],
                "test_recommendations": ["Input validation testing", "Authentication bypass attempts"]
            },
            {
                "component": "API Endpoints", 
                "description": "Health check and internal APIs",
                "potential_attacks": ["API abuse", "Injection attacks"],
                "test_recommendations": ["Rate limiting validation", "Input fuzzing"]
            },
            {
                "component": "File Upload/Processing",
                "description": "Document intelligence file handling",
                "potential_attacks": ["Malicious file upload", "Path traversal"],
                "test_recommendations": ["Malicious file testing", "Directory traversal attempts"]
            }
        ]
        
        # Test account recommendations
        prep_info["test_accounts"] = [
            {
                "account_type": "Standard User",
                "purpose": "Test standard user functionality and privilege escalation",
                "permissions": "Limited access"
            },
            {
                "account_type": "Admin User", 
                "purpose": "Test administrative functions and access controls",
                "permissions": "Full access"
            }
        ]
        
        # Network endpoints
        prep_info["network_endpoints"] = [
            {
                "service": "Web Application",
                "default_port": 8000,
                "protocol": "HTTP/HTTPS",
                "test_focus": "Authentication, session management"
            },
            {
                "service": "Health Check",
                "endpoint": "/health",
                "test_focus": "Information disclosure, service discovery"
            }
        ]
        
        # Security controls to validate
        prep_info["security_controls"] = [
            "Input validation and sanitization",
            "Authentication mechanisms",
            "Session management",
            "Authorization controls",
            "Error handling and information disclosure",
            "Rate limiting and DoS protection"
        ]
        
        # Save penetration test prep
        try:
            prep_file = self.project_root / "security" / "penetration_test_prep.json"
            with open(prep_file, 'w') as f:
                json.dump(prep_info, f, indent=2)
            
            logger.info(f"Penetration testing preparation saved to {prep_file}")
            
        except Exception as e:
            logger.error(f"Failed to save penetration test prep: {e}")
        
        return prep_info


def run_security_audit() -> SecurityAuditReport:
    """
    Main function to run a complete security audit.
    
    Returns:
        SecurityAuditReport: Complete audit results
    """
    auditor = SecurityAuditor()
    return auditor.run_full_audit()


def main():
    """Command line interface for security audit"""
    if len(sys.argv) > 1 and sys.argv[1] == "--pentest-prep":
        auditor = SecurityAuditor()
        prep_info = auditor.run_penetration_test_prep()
        print("Penetration testing preparation completed")
        print(f"Attack surfaces identified: {len(prep_info['attack_surfaces'])}")
    else:
        report = run_security_audit()
        print(f"Security audit completed with {len(report.findings)} findings")
        print(f"Risk summary: {report.risk_summary}")


if __name__ == "__main__":
    main()
