#!/usr/bin/env python3
"""
JARVIS-MK42 Alerting and Notification System
==========================================

This module provides comprehensive alerting and notification capabilities including:
- Multi-channel alert delivery (email, webhook, console)
- Alert prioritization and escalation
- Alert suppression and deduplication
- Integration with monitoring and logging systems
- Alert acknowledgment and resolution tracking
- SLA monitoring and reporting
"""

import os
import sys
import json
import time
import smtplib
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
from collections import defaultdict, deque
from pathlib import Path

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger

logger = get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert lifecycle status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ESCALATED = "escalated"


class NotificationChannel(Enum):
    """Notification delivery channels"""
    CONSOLE = "console"
    LOG = "log"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    SMS = "sms"


@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    description: str
    condition: str
    severity: AlertSeverity
    enabled: bool = True
    channels: List[NotificationChannel] = field(default_factory=list)
    cooldown_minutes: int = 5
    escalation_minutes: int = 30
    auto_resolve: bool = False
    auto_resolve_minutes: int = 60
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Active alert instance"""
    id: str
    rule_name: str
    severity: AlertSeverity
    title: str
    message: str
    created_at: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    escalated_at: Optional[datetime] = None
    notification_count: int = 0
    last_notification: Optional[datetime] = None
    source_data: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            'id': self.id,
            'rule_name': self.rule_name,
            'severity': self.severity.value,
            'title': self.title,
            'message': self.message,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'acknowledged_by': self.acknowledged_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolved_by': self.resolved_by,
            'escalated_at': self.escalated_at.isoformat() if self.escalated_at else None,
            'notification_count': self.notification_count,
            'last_notification': self.last_notification.isoformat() if self.last_notification else None,
            'source_data': self.source_data,
            'tags': self.tags,
            'metadata': self.metadata
        }


@dataclass
class NotificationConfig:
    """Notification channel configuration"""
    channel: NotificationChannel
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Email configuration
    def get_email_config(self) -> Dict[str, str]:
        return {
            'smtp_host': self.config.get('smtp_host', 'localhost'),
            'smtp_port': self.config.get('smtp_port', 587),
            'username': self.config.get('username', ''),
            'password': self.config.get('password', ''),
            'from_address': self.config.get('from_address', 'jarvis@localhost'),
            'to_addresses': self.config.get('to_addresses', [])
        }
    
    # Webhook configuration
    def get_webhook_config(self) -> Dict[str, str]:
        return {
            'url': self.config.get('url', ''),
            'method': self.config.get('method', 'POST'),
            'headers': self.config.get('headers', {}),
            'timeout': self.config.get('timeout', 30)
        }


class NotificationDelivery:
    """Notification delivery system"""
    
    def __init__(self):
        self.channels: Dict[NotificationChannel, NotificationConfig] = {}
        self._setup_default_channels()
    
    def _setup_default_channels(self):
        """Setup default notification channels"""
        # Console notifications (always enabled)
        self.channels[NotificationChannel.CONSOLE] = NotificationConfig(
            channel=NotificationChannel.CONSOLE,
            enabled=True
        )
        
        # Log notifications
        self.channels[NotificationChannel.LOG] = NotificationConfig(
            channel=NotificationChannel.LOG,
            enabled=True
        )
        
        # Email notifications (if configured)
        email_config = {
            'smtp_host': os.environ.get('SMTP_HOST', 'localhost'),
            'smtp_port': int(os.environ.get('SMTP_PORT', '587')),
            'username': os.environ.get('SMTP_USERNAME', ''),
            'password': os.environ.get('SMTP_PASSWORD', ''),
            'from_address': os.environ.get('ALERT_FROM_EMAIL', 'jarvis@localhost'),
            'to_addresses': os.environ.get('ALERT_TO_EMAILS', '').split(',') if os.environ.get('ALERT_TO_EMAILS') else []
        }
        
        self.channels[NotificationChannel.EMAIL] = NotificationConfig(
            channel=NotificationChannel.EMAIL,
            enabled=bool(email_config['to_addresses']),
            config=email_config
        )
        
        # Webhook notifications
        webhook_url = os.environ.get('ALERT_WEBHOOK_URL', '')
        self.channels[NotificationChannel.WEBHOOK] = NotificationConfig(
            channel=NotificationChannel.WEBHOOK,
            enabled=bool(webhook_url),
            config={
                'url': webhook_url,
                'method': 'POST',
                'headers': {'Content-Type': 'application/json'},
                'timeout': 30
            }
        )
    
    def deliver_notification(self, alert: Alert, channels: List[NotificationChannel] = None):
        """Deliver alert notification to specified channels"""
        if not channels:
            channels = [NotificationChannel.CONSOLE, NotificationChannel.LOG]
        
        for channel in channels:
            if channel not in self.channels or not self.channels[channel].enabled:
                continue
            
            try:
                if channel == NotificationChannel.CONSOLE:
                    self._deliver_console(alert)
                elif channel == NotificationChannel.LOG:
                    self._deliver_log(alert)
                elif channel == NotificationChannel.EMAIL:
                    self._deliver_email(alert)
                elif channel == NotificationChannel.WEBHOOK:
                    self._deliver_webhook(alert)
                else:
                    logger.warning(f"Unsupported notification channel: {channel}")
                    
            except Exception as e:
                logger.error(f"Failed to deliver notification via {channel.value}: {e}")
    
    def _deliver_console(self, alert: Alert):
        """Deliver notification to console"""
        severity_colors = {
            AlertSeverity.INFO: '\033[94m',      # Blue
            AlertSeverity.LOW: '\033[92m',       # Green
            AlertSeverity.MEDIUM: '\033[93m',    # Yellow
            AlertSeverity.HIGH: '\033[91m',      # Red
            AlertSeverity.CRITICAL: '\033[95m'   # Magenta
        }
        reset_color = '\033[0m'
        
        color = severity_colors.get(alert.severity, '')
        
        print(f"{color}[ALERT {alert.severity.value.upper()}]{reset_color} {alert.title}")
        print(f"  Message: {alert.message}")
        print(f"  Rule: {alert.rule_name}")
        print(f"  Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  ID: {alert.id}")
        print()
    
    def _deliver_log(self, alert: Alert):
        """Deliver notification to log system"""
        log_message = f"ALERT: {alert.title} | Severity: {alert.severity.value} | Rule: {alert.rule_name} | ID: {alert.id}"
        
        if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.HIGH]:
            logger.critical(log_message, extra={'alert_id': alert.id, 'severity': alert.severity.value})
        elif alert.severity == AlertSeverity.MEDIUM:
            logger.warning(log_message, extra={'alert_id': alert.id, 'severity': alert.severity.value})
        else:
            logger.info(log_message, extra={'alert_id': alert.id, 'severity': alert.severity.value})
    
    def _deliver_email(self, alert: Alert):
        """Deliver notification via email"""
        config = self.channels[NotificationChannel.EMAIL].get_email_config()
        
        if not config['to_addresses']:
            return
        
        subject = f"[JARVIS ALERT {alert.severity.value.upper()}] {alert.title}"
        
        body = f"""
JARVIS-MK42 Alert Notification

Alert ID: {alert.id}
Severity: {alert.severity.value.upper()}
Rule: {alert.rule_name}
Status: {alert.status.value}

Title: {alert.title}
Message: {alert.message}

Created: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
Notifications Sent: {alert.notification_count + 1}

Source Data: {json.dumps(alert.source_data, indent=2) if alert.source_data else 'None'}

This is an automated message from JARVIS-MK42 monitoring system.
"""
        
        try:
            msg = MIMEMultipart()
            msg['From'] = config['from_address']
            msg['To'] = ', '.join(config['to_addresses'])
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(config['smtp_host'], config['smtp_port'])
            if config['username'] and config['password']:
                server.starttls()
                server.login(config['username'], config['password'])
            
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email notification sent for alert {alert.id}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    def _deliver_webhook(self, alert: Alert):
        """Deliver notification via webhook"""
        config = self.channels[NotificationChannel.WEBHOOK].get_webhook_config()
        
        if not config['url']:
            return
        
        payload = {
            'alert': alert.to_dict(),
            'timestamp': datetime.utcnow().isoformat(),
            'source': 'JARVIS-MK42'
        }
        
        try:
            response = requests.request(
                method=config['method'],
                url=config['url'],
                json=payload,
                headers=config['headers'],
                timeout=config['timeout']
            )
            
            if response.status_code == 200:
                logger.info(f"Webhook notification sent for alert {alert.id}")
            else:
                logger.warning(f"Webhook returned status {response.status_code} for alert {alert.id}")
                
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")


class AlertManager:
    """
    Main alert management system.
    
    Handles alert creation, lifecycle management, notification delivery,
    and provides dashboard and reporting capabilities.
    """
    
    def __init__(self):
        self.active_alerts: Dict[str, Alert] = {}
        self.resolved_alerts: deque = deque(maxlen=1000)  # Keep last 1000 resolved alerts
        self.alert_rules: Dict[str, AlertRule] = {}
        self.notification_delivery = NotificationDelivery()
        self.suppressed_alerts: Set[str] = set()
        self.alert_history: deque = deque(maxlen=5000)
        self._setup_default_rules()
        self._start_background_tasks()
        logger.info("Alert manager initialized")
    
    def _setup_default_rules(self):
        """Setup default alert rules"""
        default_rules = [
            AlertRule(
                name="system_high_cpu",
                description="System CPU usage is high",
                condition="cpu_percent > 90",
                severity=AlertSeverity.HIGH,
                channels=[NotificationChannel.CONSOLE, NotificationChannel.LOG, NotificationChannel.EMAIL],
                cooldown_minutes=5,
                escalation_minutes=15
            ),
            AlertRule(
                name="system_critical_cpu",
                description="System CPU usage is critically high",
                condition="cpu_percent > 95",
                severity=AlertSeverity.CRITICAL,
                channels=[NotificationChannel.CONSOLE, NotificationChannel.LOG, NotificationChannel.EMAIL, NotificationChannel.WEBHOOK],
                cooldown_minutes=2,
                escalation_minutes=10
            ),
            AlertRule(
                name="system_high_memory",
                description="System memory usage is high",
                condition="memory_percent > 85",
                severity=AlertSeverity.MEDIUM,
                channels=[NotificationChannel.CONSOLE, NotificationChannel.LOG],
                cooldown_minutes=10,
                escalation_minutes=30
            ),
            AlertRule(
                name="application_error_rate",
                description="Application error rate is high",
                condition="error_rate > 0.1",
                severity=AlertSeverity.HIGH,
                channels=[NotificationChannel.CONSOLE, NotificationChannel.LOG, NotificationChannel.EMAIL],
                cooldown_minutes=5
            ),
            AlertRule(
                name="security_event",
                description="Security event detected",
                condition="security_event == true",
                severity=AlertSeverity.CRITICAL,
                channels=[NotificationChannel.CONSOLE, NotificationChannel.LOG, NotificationChannel.EMAIL, NotificationChannel.WEBHOOK],
                cooldown_minutes=1
            ),
            AlertRule(
                name="system_startup",
                description="System startup event",
                condition="startup_event == true",
                severity=AlertSeverity.INFO,
                channels=[NotificationChannel.CONSOLE, NotificationChannel.LOG],
                cooldown_minutes=60
            )
        ]
        
        for rule in default_rules:
            self.alert_rules[rule.name] = rule
    
    def _start_background_tasks(self):
        """Start background monitoring tasks"""
        # Escalation monitoring
        escalation_thread = threading.Thread(target=self._escalation_monitor, daemon=True)
        escalation_thread.start()
        
        # Auto-resolution monitoring
        resolution_thread = threading.Thread(target=self._resolution_monitor, daemon=True)
        resolution_thread.start()
    
    def create_alert(self, rule_name: str, title: str, message: str, 
                    source_data: Dict[str, Any] = None, tags: Dict[str, str] = None) -> Optional[str]:
        """
        Create a new alert.
        
        Args:
            rule_name: Name of the alert rule
            title: Alert title
            message: Alert message
            source_data: Source data that triggered the alert
            tags: Additional tags
            
        Returns:
            Alert ID if created, None if suppressed or rule not found
        """
        if rule_name not in self.alert_rules:
            logger.error(f"Alert rule not found: {rule_name}")
            return None
        
        rule = self.alert_rules[rule_name]
        if not rule.enabled:
            logger.debug(f"Alert rule disabled: {rule_name}")
            return None
        
        # Check for suppression
        alert_key = f"{rule_name}:{title}"
        if alert_key in self.suppressed_alerts:
            logger.debug(f"Alert suppressed: {alert_key}")
            return None
        
        # Check for existing active alert with same rule and title (deduplication)
        for alert in self.active_alerts.values():
            if alert.rule_name == rule_name and alert.title == title and alert.status == AlertStatus.ACTIVE:
                # Update existing alert instead of creating duplicate
                alert.notification_count += 1
                alert.last_notification = datetime.utcnow()
                logger.debug(f"Updated existing alert: {alert.id}")
                return alert.id
        
        # Create new alert
        alert_id = f"alert_{int(datetime.utcnow().timestamp())}_{len(self.active_alerts)}"
        
        alert = Alert(
            id=alert_id,
            rule_name=rule_name,
            severity=rule.severity,
            title=title,
            message=message,
            created_at=datetime.utcnow(),
            source_data=source_data or {},
            tags=tags or {}
        )
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Send notifications
        self.notification_delivery.deliver_notification(alert, rule.channels)
        alert.notification_count = 1
        alert.last_notification = datetime.utcnow()
        
        logger.info(f"Created alert: {alert_id} | Rule: {rule_name} | Severity: {rule.severity.value}")
        return alert_id
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """Acknowledge an alert"""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        if alert.status != AlertStatus.ACTIVE:
            return False
        
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = acknowledged_by
        
        logger.info(f"Alert acknowledged: {alert_id} by {acknowledged_by}")
        return True
    
    def resolve_alert(self, alert_id: str, resolved_by: str = "system") -> bool:
        """Resolve an alert"""
        if alert_id not in self.active_alerts:
            return False
        
        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = resolved_by
        
        # Move to resolved alerts
        self.resolved_alerts.append(alert)
        del self.active_alerts[alert_id]
        
        logger.info(f"Alert resolved: {alert_id} by {resolved_by}")
        return True
    
    def suppress_alert_pattern(self, pattern: str, duration_minutes: int = 60):
        """Suppress alerts matching a pattern"""
        self.suppressed_alerts.add(pattern)
        
        # Schedule unsuppression
        def unsuppress():
            time.sleep(duration_minutes * 60)
            self.suppressed_alerts.discard(pattern)
            logger.info(f"Alert suppression expired for pattern: {pattern}")
        
        thread = threading.Thread(target=unsuppress, daemon=True)
        thread.start()
        
        logger.info(f"Suppressed alert pattern: {pattern} for {duration_minutes} minutes")
    
    def _escalation_monitor(self):
        """Monitor alerts for escalation"""
        while True:
            try:
                now = datetime.utcnow()
                
                for alert in list(self.active_alerts.values()):
                    if alert.status == AlertStatus.ACTIVE and not alert.escalated_at:
                        rule = self.alert_rules.get(alert.rule_name)
                        if rule and rule.escalation_minutes > 0:
                            escalation_time = alert.created_at + timedelta(minutes=rule.escalation_minutes)
                            
                            if now >= escalation_time:
                                self._escalate_alert(alert)
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in escalation monitor: {e}")
                time.sleep(60)
    
    def _escalate_alert(self, alert: Alert):
        """Escalate an unacknowledged alert"""
        alert.status = AlertStatus.ESCALATED
        alert.escalated_at = datetime.utcnow()
        
        # Send escalation notification with higher priority
        escalated_title = f"ESCALATED: {alert.title}"
        escalated_message = f"This alert has been escalated due to no acknowledgment.\n\nOriginal message: {alert.message}"
        
        escalated_alert = Alert(
            id=f"{alert.id}_escalated",
            rule_name=alert.rule_name,
            severity=AlertSeverity.CRITICAL,
            title=escalated_title,
            message=escalated_message,
            created_at=datetime.utcnow(),
            source_data=alert.source_data,
            tags=alert.tags
        )
        
        # Use all available channels for escalated alerts
        all_channels = [NotificationChannel.CONSOLE, NotificationChannel.LOG, 
                       NotificationChannel.EMAIL, NotificationChannel.WEBHOOK]
        self.notification_delivery.deliver_notification(escalated_alert, all_channels)
        
        logger.warning(f"Alert escalated: {alert.id}")
    
    def _resolution_monitor(self):
        """Monitor alerts for auto-resolution"""
        while True:
            try:
                now = datetime.utcnow()
                
                for alert_id, alert in list(self.active_alerts.items()):
                    rule = self.alert_rules.get(alert.rule_name)
                    if rule and rule.auto_resolve:
                        resolution_time = alert.created_at + timedelta(minutes=rule.auto_resolve_minutes)
                        
                        if now >= resolution_time and alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]:
                            self.resolve_alert(alert_id, "auto-resolution")
                
                time.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in resolution monitor: {e}")
                time.sleep(300)
    
    def get_alert_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive alert dashboard data"""
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        
        # Active alerts by severity
        active_by_severity = defaultdict(int)
        for alert in self.active_alerts.values():
            active_by_severity[alert.severity.value] += 1
        
        # Recent alert history
        recent_alerts = [alert for alert in self.alert_history if alert.created_at >= last_24h]
        
        # Alert statistics
        stats = {
            'active_alerts': len(self.active_alerts),
            'resolved_alerts_24h': len([alert for alert in self.resolved_alerts if alert.resolved_at and alert.resolved_at >= last_24h]),
            'total_alerts_24h': len(recent_alerts),
            'escalated_alerts': len([alert for alert in self.active_alerts.values() if alert.status == AlertStatus.ESCALATED]),
            'acknowledged_alerts': len([alert for alert in self.active_alerts.values() if alert.status == AlertStatus.ACKNOWLEDGED])
        }
        
        return {
            'timestamp': now.isoformat(),
            'statistics': stats,
            'active_alerts_by_severity': dict(active_by_severity),
            'active_alerts': [alert.to_dict() for alert in self.active_alerts.values()],
            'recent_resolved': [alert.to_dict() for alert in list(self.resolved_alerts)[-10:]],
            'alert_rules_count': len(self.alert_rules),
            'suppressed_patterns': list(self.suppressed_alerts)
        }
    
    def get_sla_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate SLA report for alert handling"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get alerts from the time period
        period_alerts = [alert for alert in self.alert_history if alert.created_at >= since]
        
        # Calculate metrics
        total_alerts = len(period_alerts)
        acknowledged_alerts = len([a for a in period_alerts if a.acknowledged_at])
        resolved_alerts = len([a for a in period_alerts if a.resolved_at])
        escalated_alerts = len([a for a in period_alerts if a.escalated_at])
        
        # Response times
        ack_times = []
        resolution_times = []
        
        for alert in period_alerts:
            if alert.acknowledged_at:
                ack_time = (alert.acknowledged_at - alert.created_at).total_seconds() / 60  # minutes
                ack_times.append(ack_time)
            
            if alert.resolved_at:
                resolution_time = (alert.resolved_at - alert.created_at).total_seconds() / 60  # minutes
                resolution_times.append(resolution_time)
        
        avg_ack_time = sum(ack_times) / len(ack_times) if ack_times else 0
        avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
        
        return {
            'period_hours': hours,
            'total_alerts': total_alerts,
            'acknowledged_rate': acknowledged_alerts / total_alerts if total_alerts else 0,
            'resolution_rate': resolved_alerts / total_alerts if total_alerts else 0,
            'escalation_rate': escalated_alerts / total_alerts if total_alerts else 0,
            'avg_acknowledgment_time_minutes': round(avg_ack_time, 2),
            'avg_resolution_time_minutes': round(avg_resolution_time, 2),
            'sla_metrics': {
                'acknowledgment_sla_15min': len([t for t in ack_times if t <= 15]) / len(ack_times) if ack_times else 0,
                'resolution_sla_60min': len([t for t in resolution_times if t <= 60]) / len(resolution_times) if resolution_times else 0
            }
        }


# Global alert manager instance
_alert_manager = None

def get_alert_manager() -> AlertManager:
    """Get or create the global alert manager instance"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager


def create_alert(rule_name: str, title: str, message: str, 
                source_data: Dict[str, Any] = None, tags: Dict[str, str] = None) -> Optional[str]:
    """Convenience function to create an alert"""
    manager = get_alert_manager()
    return manager.create_alert(rule_name, title, message, source_data, tags)


def main():
    """Command line interface for alerting system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 Alerting System")
    parser.add_argument('--dashboard', action='store_true', help='Show alert dashboard')
    parser.add_argument('--create', nargs=3, metavar=('rule', 'title', 'message'), help='Create test alert')
    parser.add_argument('--acknowledge', help='Acknowledge alert by ID')
    parser.add_argument('--resolve', help='Resolve alert by ID')
    parser.add_argument('--sla', type=int, default=24, help='Generate SLA report for N hours')
    
    args = parser.parse_args()
    
    manager = get_alert_manager()
    
    if args.dashboard:
        dashboard = manager.get_alert_dashboard()
        print(json.dumps(dashboard, indent=2))
    
    elif args.create:
        rule_name, title, message = args.create
        alert_id = manager.create_alert(rule_name, title, message)
        if alert_id:
            print(f"Created alert: {alert_id}")
        else:
            print("Failed to create alert")
    
    elif args.acknowledge:
        success = manager.acknowledge_alert(args.acknowledge, "CLI")
        print(f"Acknowledge {'successful' if success else 'failed'}")
    
    elif args.resolve:
        success = manager.resolve_alert(args.resolve, "CLI")
        print(f"Resolution {'successful' if success else 'failed'}")
    
    elif args.sla:
        report = manager.get_sla_report(args.sla)
        print(json.dumps(report, indent=2))
    
    else:
        print("JARVIS-MK42 Alerting System")
        print("Use --dashboard, --create, --acknowledge, --resolve, or --sla")


if __name__ == "__main__":
    main()
