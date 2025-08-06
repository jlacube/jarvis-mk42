#!/usr/bin/env python3
"""
JARVIS-MK42 Data Retention & Archival System
===========================================

This module provides comprehensive data lifecycle management including:
- Automated data retention policies and enforcement
- Intelligent data archival and compression
- Compliance tracking and audit trails
- Data classification and categorization
- Automated purging of expired data
- Archive retrieval and restoration
- Legal hold and regulatory compliance
- Storage optimization through tiered storage
"""

import os
import sys
import json
import gzip
import shutil
import sqlite3
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict, namedtuple
import re

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger

logger = get_logger(__name__)


class DataClassification(Enum):
    """Data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    PERSONAL = "personal"
    SENSITIVE = "sensitive"


class RetentionAction(Enum):
    """Actions to take when retention period expires"""
    DELETE = "delete"
    ARCHIVE = "archive"
    REVIEW = "review"
    LEGAL_HOLD = "legal_hold"
    EXTEND = "extend"


class ArchiveStatus(Enum):
    """Status of archived data"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ARCHIVED = "archived"
    FAILED = "failed"
    RESTORED = "restored"
    DELETED = "deleted"


class ComplianceFramework(Enum):
    """Compliance frameworks"""
    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"
    CUSTOM = "custom"


@dataclass
class RetentionPolicy:
    """Data retention policy definition"""
    policy_id: str
    name: str
    description: str
    data_types: List[str]
    classification_levels: List[DataClassification]
    retention_period_days: int
    action_on_expiry: RetentionAction
    compliance_frameworks: List[ComplianceFramework] = field(default_factory=list)
    created_by: str = "system"
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_modified: datetime = field(default_factory=datetime.utcnow)
    enabled: bool = True
    legal_hold_override: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'policy_id': self.policy_id,
            'name': self.name,
            'description': self.description,
            'data_types': self.data_types,
            'classification_levels': [c.value for c in self.classification_levels],
            'retention_period_days': self.retention_period_days,
            'action_on_expiry': self.action_on_expiry.value,
            'compliance_frameworks': [f.value for f in self.compliance_frameworks],
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat(),
            'last_modified': self.last_modified.isoformat(),
            'enabled': self.enabled,
            'legal_hold_override': self.legal_hold_override
        }


@dataclass
class DataRecord:
    """Individual data record with retention metadata"""
    record_id: str
    data_type: str
    classification: DataClassification
    source_location: str
    size_bytes: int
    created_at: datetime
    last_accessed: datetime
    last_modified: datetime
    retention_policy_id: str
    expiry_date: datetime
    legal_hold: bool = False
    legal_hold_reason: str = ""
    archive_location: Optional[str] = None
    archive_status: ArchiveStatus = ArchiveStatus.PENDING
    checksum: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'record_id': self.record_id,
            'data_type': self.data_type,
            'classification': self.classification.value,
            'source_location': self.source_location,
            'size_bytes': self.size_bytes,
            'size_mb': round(self.size_bytes / (1024 * 1024), 4),
            'created_at': self.created_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'last_modified': self.last_modified.isoformat(),
            'retention_policy_id': self.retention_policy_id,
            'expiry_date': self.expiry_date.isoformat(),
            'legal_hold': self.legal_hold,
            'legal_hold_reason': self.legal_hold_reason,
            'archive_location': self.archive_location,
            'archive_status': self.archive_status.value,
            'checksum': self.checksum,
            'metadata': self.metadata
        }


@dataclass
class AuditEvent:
    """Audit event for compliance tracking"""
    event_id: str
    timestamp: datetime
    event_type: str
    record_id: str
    policy_id: str
    action_taken: str
    reason: str
    user: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'record_id': self.record_id,
            'policy_id': self.policy_id,
            'action_taken': self.action_taken,
            'reason': self.reason,
            'user': self.user,
            'details': self.details
        }


@dataclass
class ArchiveJob:
    """Archive job definition"""
    job_id: str
    created_at: datetime
    status: ArchiveStatus
    source_records: List[str]
    archive_location: str
    compression_ratio: float = 0.0
    bytes_processed: int = 0
    error_message: str = ""
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'job_id': self.job_id,
            'created_at': self.created_at.isoformat(),
            'status': self.status.value,
            'source_records': self.source_records,
            'archive_location': self.archive_location,
            'compression_ratio': self.compression_ratio,
            'bytes_processed': self.bytes_processed,
            'bytes_processed_mb': round(self.bytes_processed / (1024 * 1024), 2),
            'error_message': self.error_message,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class DataClassifier:
    """Classifies data based on content and metadata"""
    
    def __init__(self):
        self.classification_rules = self._get_default_classification_rules()
    
    def _get_default_classification_rules(self) -> Dict[str, Dict[str, Any]]:
        """Get default data classification rules"""
        return {
            'personal_data': {
                'patterns': [
                    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
                    r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
                    r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card
                    r'\b\d{3}[\s-]?\d{3}[\s-]?\d{4}\b',  # Phone number
                ],
                'classification': DataClassification.PERSONAL,
                'keywords': ['name', 'address', 'email', 'phone', 'ssn', 'dob', 'birth']
            },
            'sensitive_data': {
                'patterns': [
                    r'password[s]?[\s:=]+\S+',  # Passwords
                    r'api[_\s]?key[s]?[\s:=]+\S+',  # API keys
                    r'secret[s]?[\s:=]+\S+',  # Secrets
                ],
                'classification': DataClassification.SENSITIVE,
                'keywords': ['password', 'secret', 'key', 'token', 'credential']
            },
            'confidential_data': {
                'patterns': [
                    r'\bconfidential\b',
                    r'\bproprietary\b',
                    r'\btrade\s+secret\b',
                ],
                'classification': DataClassification.CONFIDENTIAL,
                'keywords': ['confidential', 'proprietary', 'internal', 'restricted']
            }
        }
    
    def classify_content(self, content: str, filename: str = "") -> DataClassification:
        """
        Classify content based on patterns and keywords.
        
        Args:
            content: Text content to classify
            filename: Optional filename for additional context
            
        Returns:
            DataClassification level
        """
        content_lower = content.lower()
        filename_lower = filename.lower()
        
        # Check for sensitive patterns first (highest priority)
        for rule_name, rule in self.classification_rules.items():
            # Check patterns
            for pattern in rule['patterns']:
                if re.search(pattern, content, re.IGNORECASE):
                    return rule['classification']
            
            # Check keywords
            for keyword in rule['keywords']:
                if keyword in content_lower or keyword in filename_lower:
                    return rule['classification']
        
        # Default classification
        return DataClassification.INTERNAL
    
    def classify_file(self, file_path: Path) -> DataClassification:
        """Classify a file based on its content and metadata"""
        try:
            # Check file extension for quick classification
            suffix = file_path.suffix.lower()
            
            # Skip binary files that are unlikely to contain sensitive text data
            binary_extensions = {'.exe', '.dll', '.so', '.dylib', '.bin', '.dat', '.img', '.iso'}
            if suffix in binary_extensions:
                return DataClassification.INTERNAL
            
            # Try to read and classify text content
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                return self.classify_content(content, file_path.name)
            except (UnicodeDecodeError, PermissionError):
                # If we can't read the file as text, classify based on filename
                return self.classify_content("", file_path.name)
        
        except Exception as e:
            logger.warning("Error classifying file %s: %s", file_path, e)
            return DataClassification.INTERNAL


class ArchiveManager:
    """Manages data archival operations"""
    
    def __init__(self, archive_root: str = "archives"):
        self.archive_root = Path(archive_root)
        self.archive_root.mkdir(exist_ok=True)
        self.active_jobs: Dict[str, ArchiveJob] = {}
        self.lock = threading.RLock()
    
    def create_archive(self, records: List[DataRecord], archive_name: str) -> str:
        """
        Create an archive from data records.
        
        Args:
            records: List of data records to archive
            archive_name: Name for the archive
            
        Returns:
            Archive job ID
        """
        job_id = f"archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(records)}"
        
        archive_job = ArchiveJob(
            job_id=job_id,
            created_at=datetime.utcnow(),
            status=ArchiveStatus.PENDING,
            source_records=[r.record_id for r in records],
            archive_location=str(self.archive_root / f"{archive_name}.tar.gz")
        )
        
        with self.lock:
            self.active_jobs[job_id] = archive_job
        
        # Start archive creation in background thread
        threading.Thread(target=self._create_archive_async, args=(job_id, records), daemon=True).start()
        
        logger.info("Archive job started: %s (%d records)", job_id, len(records))
        return job_id
    
    def _create_archive_async(self, job_id: str, records: List[DataRecord]):
        """Create archive asynchronously"""
        import tarfile
        
        job = self.active_jobs[job_id]
        job.status = ArchiveStatus.IN_PROGRESS
        
        try:
            total_uncompressed = 0
            
            with tarfile.open(job.archive_location, 'w:gz') as tar:
                for record in records:
                    source_path = Path(record.source_location)
                    if source_path.exists():
                        # Add file to archive
                        tar.add(source_path, arcname=f"{record.record_id}/{source_path.name}")
                        total_uncompressed += source_path.stat().st_size
                        job.bytes_processed += source_path.stat().st_size
            
            # Calculate compression ratio
            compressed_size = Path(job.archive_location).stat().st_size
            job.compression_ratio = 1 - (compressed_size / total_uncompressed) if total_uncompressed > 0 else 0
            job.status = ArchiveStatus.ARCHIVED
            job.completed_at = datetime.utcnow()
            
            logger.info("Archive created successfully: %s (compression: %.1f%%)", 
                       job_id, job.compression_ratio * 100)
            
        except Exception as e:
            job.status = ArchiveStatus.FAILED
            job.error_message = str(e)
            logger.error("Archive creation failed for %s: %s", job_id, e)
    
    def restore_from_archive(self, archive_path: str, restore_path: str, record_ids: List[str] = None) -> bool:
        """
        Restore data from archive.
        
        Args:
            archive_path: Path to the archive file
            restore_path: Path where to restore the data
            record_ids: Specific record IDs to restore (None for all)
            
        Returns:
            True if restoration was successful
        """
        import tarfile
        
        try:
            restore_dir = Path(restore_path)
            restore_dir.mkdir(parents=True, exist_ok=True)
            
            with tarfile.open(archive_path, 'r:gz') as tar:
                if record_ids:
                    # Restore only specific records
                    for record_id in record_ids:
                        try:
                            # Extract files belonging to this record
                            members = [m for m in tar.getmembers() if m.name.startswith(f"{record_id}/")]
                            for member in members:
                                tar.extract(member, restore_dir)
                        except KeyError:
                            logger.warning("Record %s not found in archive", record_id)
                else:
                    # Restore all records
                    tar.extractall(restore_dir)
            
            logger.info("Archive restored successfully to: %s", restore_path)
            return True
            
        except Exception as e:
            logger.error("Archive restoration failed: %s", e)
            return False
    
    def get_archive_info(self, archive_path: str) -> Dict[str, Any]:
        """Get information about an archive"""
        import tarfile
        
        try:
            archive_info = {
                'path': archive_path,
                'size': Path(archive_path).stat().st_size,
                'created': datetime.fromtimestamp(Path(archive_path).stat().st_ctime),
                'records': [],
                'total_files': 0
            }
            
            with tarfile.open(archive_path, 'r:gz') as tar:
                record_files = defaultdict(list)
                
                for member in tar.getmembers():
                    if member.isfile():
                        archive_info['total_files'] += 1
                        # Extract record ID from path
                        parts = member.name.split('/', 1)
                        if len(parts) >= 2:
                            record_id = parts[0]
                            record_files[record_id].append({
                                'name': parts[1],
                                'size': member.size,
                                'modified': datetime.fromtimestamp(member.mtime)
                            })
                
                archive_info['records'] = [
                    {'record_id': rid, 'files': files} 
                    for rid, files in record_files.items()
                ]
            
            return archive_info
            
        except Exception as e:
            logger.error("Error getting archive info for %s: %s", archive_path, e)
            return {'error': str(e)}
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of an archive job"""
        with self.lock:
            job = self.active_jobs.get(job_id)
            return job.to_dict() if job else None


class RetentionArchivalSystem:
    """
    Main data retention and archival system.
    
    Provides comprehensive data lifecycle management including
    retention policies, archival, compliance tracking, and audit trails.
    """
    
    def __init__(self, base_path: str = ".", database_path: str = "retention.db"):
        self.base_path = Path(base_path).resolve()
        self.database_path = database_path
        self.classifier = DataClassifier()
        self.archive_manager = ArchiveManager()
        
        # In-memory storage for policies and records
        self.retention_policies: Dict[str, RetentionPolicy] = {}
        self.data_records: Dict[str, DataRecord] = {}
        self.audit_events: List[AuditEvent] = []
        
        self.lock = threading.RLock()
        
        # Initialize database and load data
        self._initialize_database()
        self._load_default_policies()
        
        logger.info("Data Retention & Archival System initialized for path: %s", self.base_path)
    
    def _initialize_database(self):
        """Initialize the SQLite database for persistence"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS retention_policies (
                    policy_id TEXT PRIMARY KEY,
                    policy_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_records (
                    record_id TEXT PRIMARY KEY,
                    record_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    event_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_records_expiry ON data_records(json_extract(record_data, "$.expiry_date"))')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_records_policy ON data_records(json_extract(record_data, "$.retention_policy_id"))')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(created_at)')
            
            conn.commit()
            conn.close()
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error("Error initializing database: %s", e)
    
    def _load_default_policies(self):
        """Load default retention policies"""
        default_policies = [
            RetentionPolicy(
                policy_id="logs_standard",
                name="Standard Log Retention",
                description="Standard retention for application logs",
                data_types=["log", "audit_log", "error_log"],
                classification_levels=[DataClassification.INTERNAL],
                retention_period_days=90,
                action_on_expiry=RetentionAction.ARCHIVE
            ),
            RetentionPolicy(
                policy_id="personal_data_gdpr",
                name="GDPR Personal Data",
                description="GDPR compliant retention for personal data",
                data_types=["user_data", "personal_info", "profile"],
                classification_levels=[DataClassification.PERSONAL],
                retention_period_days=2555,  # 7 years
                action_on_expiry=RetentionAction.DELETE,
                compliance_frameworks=[ComplianceFramework.GDPR]
            ),
            RetentionPolicy(
                policy_id="temp_data_cleanup",
                name="Temporary Data Cleanup",
                description="Quick cleanup of temporary and cache data",
                data_types=["temp", "cache", "session"],
                classification_levels=[DataClassification.INTERNAL],
                retention_period_days=7,
                action_on_expiry=RetentionAction.DELETE
            ),
            RetentionPolicy(
                policy_id="sensitive_data_secure",
                name="Sensitive Data Security",
                description="Secure handling of sensitive business data",
                data_types=["financial", "proprietary", "strategic"],
                classification_levels=[DataClassification.CONFIDENTIAL, DataClassification.SENSITIVE],
                retention_period_days=2555,  # 7 years
                action_on_expiry=RetentionAction.REVIEW
            )
        ]
        
        for policy in default_policies:
            self.create_retention_policy(policy)
    
    def create_retention_policy(self, policy: RetentionPolicy) -> bool:
        """
        Create a new retention policy.
        
        Args:
            policy: RetentionPolicy object
            
        Returns:
            True if policy was created successfully
        """
        try:
            with self.lock:
                self.retention_policies[policy.policy_id] = policy
            
            # Persist to database
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO retention_policies (policy_id, policy_data) VALUES (?, ?)',
                (policy.policy_id, json.dumps(policy.to_dict()))
            )
            conn.commit()
            conn.close()
            
            self._create_audit_event(
                event_type="policy_created",
                record_id="",
                policy_id=policy.policy_id,
                action_taken="create_policy",
                reason=f"Created retention policy: {policy.name}",
                user="system"
            )
            
            logger.info("Retention policy created: %s", policy.policy_id)
            return True
            
        except Exception as e:
            logger.error("Error creating retention policy: %s", e)
            return False
    
    def register_data_record(self, file_path: Path, data_type: str = "file") -> Optional[str]:
        """
        Register a data record for retention management.
        
        Args:
            file_path: Path to the data file
            data_type: Type of data (for policy matching)
            
        Returns:
            Record ID if successful, None otherwise
        """
        try:
            if not file_path.exists():
                logger.warning("File not found: %s", file_path)
                return None
            
            stat = file_path.stat()
            
            # Classify the file
            classification = self.classifier.classify_file(file_path)
            
            # Find matching retention policy
            policy = self._find_matching_policy(data_type, classification)
            if not policy:
                logger.warning("No matching retention policy for %s (%s)", file_path, data_type)
                return None
            
            # Calculate expiry date
            expiry_date = datetime.utcnow() + timedelta(days=policy.retention_period_days)
            
            # Calculate checksum
            checksum = self._calculate_checksum(file_path)
            
            # Create record
            record_id = f"rec_{hashlib.md5(str(file_path).encode()).hexdigest()[:12]}"
            
            record = DataRecord(
                record_id=record_id,
                data_type=data_type,
                classification=classification,
                source_location=str(file_path),
                size_bytes=stat.st_size,
                created_at=datetime.fromtimestamp(stat.st_ctime),
                last_accessed=datetime.fromtimestamp(stat.st_atime),
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                retention_policy_id=policy.policy_id,
                expiry_date=expiry_date,
                checksum=checksum
            )
            
            with self.lock:
                self.data_records[record_id] = record
            
            # Persist to database
            self._persist_record(record)
            
            self._create_audit_event(
                event_type="record_registered",
                record_id=record_id,
                policy_id=policy.policy_id,
                action_taken="register_record",
                reason=f"Registered data record: {file_path.name}",
                user="system"
            )
            
            logger.debug("Data record registered: %s (%s)", record_id, file_path.name)
            return record_id
            
        except Exception as e:
            logger.error("Error registering data record for %s: %s", file_path, e)
            return None
    
    def _find_matching_policy(self, data_type: str, classification: DataClassification) -> Optional[RetentionPolicy]:
        """Find the best matching retention policy for data type and classification"""
        best_policy = None
        best_score = 0
        
        for policy in self.retention_policies.values():
            if not policy.enabled:
                continue
            
            score = 0
            
            # Check data type match
            if data_type in policy.data_types:
                score += 10
            elif any(dt in data_type for dt in policy.data_types):
                score += 5
            
            # Check classification match
            if classification in policy.classification_levels:
                score += 10
            
            if score > best_score:
                best_score = score
                best_policy = policy
        
        return best_policy
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file"""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.warning("Error calculating checksum for %s: %s", file_path, e)
            return ""
    
    def _persist_record(self, record: DataRecord):
        """Persist data record to database"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO data_records (record_id, record_data) VALUES (?, ?)',
                (record.record_id, json.dumps(record.to_dict()))
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Error persisting record %s: %s", record.record_id, e)
    
    def scan_directory(self, directory: Path = None, data_type: str = "file") -> Dict[str, Any]:
        """
        Scan directory and register all files for retention management.
        
        Args:
            directory: Directory to scan (None for base path)
            data_type: Default data type for discovered files
            
        Returns:
            Dictionary with scan results
        """
        if directory is None:
            directory = self.base_path
        
        logger.info("Scanning directory for data records: %s", directory)
        
        results = {
            'scanned_files': 0,
            'registered_records': 0,
            'skipped_files': 0,
            'errors': 0,
            'by_classification': defaultdict(int),
            'by_data_type': defaultdict(int)
        }
        
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                results['scanned_files'] += 1
                
                try:
                    # Try to determine data type from file
                    inferred_type = self._infer_data_type(file_path)
                    record_id = self.register_data_record(file_path, inferred_type or data_type)
                    
                    if record_id:
                        results['registered_records'] += 1
                        record = self.data_records[record_id]
                        results['by_classification'][record.classification.value] += 1
                        results['by_data_type'][record.data_type] += 1
                    else:
                        results['skipped_files'] += 1
                        
                except Exception as e:
                    results['errors'] += 1
                    logger.error("Error processing file %s: %s", file_path, e)
        
        logger.info("Directory scan completed: %d files scanned, %d records registered", 
                   results['scanned_files'], results['registered_records'])
        
        return results
    
    def _infer_data_type(self, file_path: Path) -> Optional[str]:
        """Infer data type from file path and extension"""
        name = file_path.name.lower()
        suffix = file_path.suffix.lower()
        
        # Log files
        if 'log' in name or suffix == '.log':
            return 'log'
        
        # Configuration files
        if suffix in ['.conf', '.config', '.ini', '.yaml', '.yml', '.json'] or 'config' in name:
            return 'config'
        
        # Database files
        if suffix in ['.db', '.sqlite', '.sqlite3']:
            return 'database'
        
        # Backup files
        if suffix in ['.bak', '.backup'] or 'backup' in name:
            return 'backup'
        
        # Temporary files
        if suffix in ['.tmp', '.temp'] or 'temp' in name or 'cache' in name:
            return 'temp'
        
        return None
    
    def process_expired_records(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Process records that have reached their retention expiry date.
        
        Args:
            dry_run: If True, only simulate processing without taking action
            
        Returns:
            Dictionary with processing results
        """
        logger.info("Processing expired records (dry_run=%s)", dry_run)
        
        now = datetime.utcnow()
        expired_records = []
        
        # Find expired records
        for record in self.data_records.values():
            if record.expiry_date <= now and not record.legal_hold:
                expired_records.append(record)
        
        results = {
            'total_expired': len(expired_records),
            'actions_taken': defaultdict(int),
            'space_freed': 0,
            'archived_records': [],
            'deleted_records': [],
            'errors': []
        }
        
        # Group by retention policy action
        by_action = defaultdict(list)
        for record in expired_records:
            policy = self.retention_policies.get(record.retention_policy_id)
            if policy:
                by_action[policy.action_on_expiry].append(record)
        
        # Process each action group
        for action, records in by_action.items():
            try:
                if action == RetentionAction.DELETE:
                    result = self._delete_records(records, dry_run)
                    results['actions_taken']['delete'] += result['deleted_count']
                    results['space_freed'] += result['space_freed']
                    results['deleted_records'].extend(result['deleted_records'])
                    results['errors'].extend(result['errors'])
                
                elif action == RetentionAction.ARCHIVE:
                    result = self._archive_records(records, dry_run)
                    results['actions_taken']['archive'] += result['archived_count']
                    results['archived_records'].extend(result['archived_records'])
                    results['errors'].extend(result['errors'])
                
                elif action == RetentionAction.REVIEW:
                    # Mark for manual review
                    for record in records:
                        if not dry_run:
                            record.metadata['requires_review'] = True
                            record.metadata['review_requested_at'] = now.isoformat()
                            self._persist_record(record)
                    results['actions_taken']['review'] += len(records)
                
                elif action == RetentionAction.EXTEND:
                    # Extend retention period by the original period
                    for record in records:
                        if not dry_run:
                            policy = self.retention_policies.get(record.retention_policy_id)
                            if policy:
                                record.expiry_date = now + timedelta(days=policy.retention_period_days)
                                self._persist_record(record)
                    results['actions_taken']['extend'] += len(records)
                
            except Exception as e:
                logger.error("Error processing records for action %s: %s", action, e)
                results['errors'].append(f"Action {action.value}: {str(e)}")
        
        logger.info("Expired records processing completed: %d records processed", 
                   results['total_expired'])
        
        return results
    
    def _delete_records(self, records: List[DataRecord], dry_run: bool) -> Dict[str, Any]:
        """Delete expired records"""
        result = {
            'deleted_count': 0,
            'space_freed': 0,
            'deleted_records': [],
            'errors': []
        }
        
        for record in records:
            try:
                source_path = Path(record.source_location)
                
                if source_path.exists():
                    space_freed = source_path.stat().st_size
                    
                    if not dry_run:
                        source_path.unlink()
                        
                        # Remove from tracking
                        with self.lock:
                            if record.record_id in self.data_records:
                                del self.data_records[record.record_id]
                        
                        # Remove from database
                        conn = sqlite3.connect(self.database_path)
                        cursor = conn.cursor()
                        cursor.execute('DELETE FROM data_records WHERE record_id = ?', (record.record_id,))
                        conn.commit()
                        conn.close()
                        
                        # Create audit event
                        self._create_audit_event(
                            event_type="record_deleted",
                            record_id=record.record_id,
                            policy_id=record.retention_policy_id,
                            action_taken="delete_expired",
                            reason="Retention period expired",
                            user="system"
                        )
                    
                    result['deleted_count'] += 1
                    result['space_freed'] += space_freed
                    result['deleted_records'].append({
                        'record_id': record.record_id,
                        'path': record.source_location,
                        'size': space_freed
                    })
                    
                    logger.debug("Record deleted: %s (%s)", record.record_id, source_path.name)
                
            except Exception as e:
                error_msg = f"Error deleting record {record.record_id}: {str(e)}"
                result['errors'].append(error_msg)
                logger.error(error_msg)
        
        return result
    
    def _archive_records(self, records: List[DataRecord], dry_run: bool) -> Dict[str, Any]:
        """Archive expired records"""
        result = {
            'archived_count': 0,
            'archived_records': [],
            'errors': []
        }
        
        if not records:
            return result
        
        try:
            if not dry_run:
                # Create archive
                archive_name = f"expired_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                job_id = self.archive_manager.create_archive(records, archive_name)
                
                # Update record status
                for record in records:
                    record.archive_status = ArchiveStatus.ARCHIVED
                    record.metadata['archive_job_id'] = job_id
                    self._persist_record(record)
                    
                    # Create audit event
                    self._create_audit_event(
                        event_type="record_archived",
                        record_id=record.record_id,
                        policy_id=record.retention_policy_id,
                        action_taken="archive_expired",
                        reason="Retention period expired - archived for compliance",
                        user="system",
                        details={'archive_job_id': job_id}
                    )
                
                result['archived_records'].append({
                    'job_id': job_id,
                    'record_count': len(records),
                    'records': [r.record_id for r in records]
                })
            
            result['archived_count'] = len(records)
            
            logger.info("Records archived: %d records in job %s", len(records), 
                       job_id if not dry_run else "DRY_RUN")
            
        except Exception as e:
            error_msg = f"Error archiving records: {str(e)}"
            result['errors'].append(error_msg)
            logger.error(error_msg)
        
        return result
    
    def apply_legal_hold(self, record_ids: List[str], reason: str, user: str = "system") -> Dict[str, Any]:
        """
        Apply legal hold to prevent deletion of records.
        
        Args:
            record_ids: List of record IDs to hold
            reason: Reason for the legal hold
            user: User applying the hold
            
        Returns:
            Dictionary with results
        """
        result = {
            'applied_count': 0,
            'not_found': [],
            'errors': []
        }
        
        for record_id in record_ids:
            try:
                with self.lock:
                    record = self.data_records.get(record_id)
                    if record:
                        record.legal_hold = True
                        record.legal_hold_reason = reason
                        self._persist_record(record)
                        
                        self._create_audit_event(
                            event_type="legal_hold_applied",
                            record_id=record_id,
                            policy_id=record.retention_policy_id,
                            action_taken="apply_legal_hold",
                            reason=reason,
                            user=user
                        )
                        
                        result['applied_count'] += 1
                        logger.info("Legal hold applied to record: %s", record_id)
                    else:
                        result['not_found'].append(record_id)
                        
            except Exception as e:
                error_msg = f"Error applying legal hold to {record_id}: {str(e)}"
                result['errors'].append(error_msg)
                logger.error(error_msg)
        
        return result
    
    def remove_legal_hold(self, record_ids: List[str], user: str = "system") -> Dict[str, Any]:
        """Remove legal hold from records"""
        result = {
            'removed_count': 0,
            'not_found': [],
            'errors': []
        }
        
        for record_id in record_ids:
            try:
                with self.lock:
                    record = self.data_records.get(record_id)
                    if record:
                        record.legal_hold = False
                        record.legal_hold_reason = ""
                        self._persist_record(record)
                        
                        self._create_audit_event(
                            event_type="legal_hold_removed",
                            record_id=record_id,
                            policy_id=record.retention_policy_id,
                            action_taken="remove_legal_hold",
                            reason="Legal hold released",
                            user=user
                        )
                        
                        result['removed_count'] += 1
                        logger.info("Legal hold removed from record: %s", record_id)
                    else:
                        result['not_found'].append(record_id)
                        
            except Exception as e:
                error_msg = f"Error removing legal hold from {record_id}: {str(e)}"
                result['errors'].append(error_msg)
                logger.error(error_msg)
        
        return result
    
    def _create_audit_event(self, event_type: str, record_id: str, policy_id: str,
                          action_taken: str, reason: str, user: str, details: Dict[str, Any] = None):
        """Create an audit event"""
        event_id = f"audit_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        
        event = AuditEvent(
            event_id=event_id,
            timestamp=datetime.utcnow(),
            event_type=event_type,
            record_id=record_id,
            policy_id=policy_id,
            action_taken=action_taken,
            reason=reason,
            user=user,
            details=details or {}
        )
        
        self.audit_events.append(event)
        
        # Persist to database
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO audit_events (event_id, event_data) VALUES (?, ?)',
                (event_id, json.dumps(event.to_dict()))
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Error persisting audit event: %s", e)
    
    def get_compliance_report(self, framework: ComplianceFramework = None, 
                            days: int = 30) -> Dict[str, Any]:
        """
        Generate compliance report.
        
        Args:
            framework: Specific compliance framework (None for all)
            days: Number of days to include in the report
            
        Returns:
            Compliance report dictionary
        """
        since = datetime.utcnow() - timedelta(days=days)
        
        # Filter audit events
        relevant_events = [
            event for event in self.audit_events
            if event.timestamp >= since
        ]
        
        # Filter policies by framework
        relevant_policies = []
        for policy in self.retention_policies.values():
            if framework is None or framework in policy.compliance_frameworks:
                relevant_policies.append(policy)
        
        # Count records by policy
        records_by_policy = defaultdict(int)
        expired_records = 0
        legal_hold_records = 0
        
        for record in self.data_records.values():
            records_by_policy[record.retention_policy_id] += 1
            if record.expiry_date <= datetime.utcnow():
                expired_records += 1
            if record.legal_hold:
                legal_hold_records += 1
        
        # Analyze audit events
        event_summary = defaultdict(int)
        for event in relevant_events:
            event_summary[event.event_type] += 1
        
        report = {
            'framework': framework.value if framework else 'all',
            'report_period_days': days,
            'generated_at': datetime.utcnow().isoformat(),
            'policies': {
                'total_policies': len(relevant_policies),
                'by_framework': defaultdict(int),
                'policies': [p.to_dict() for p in relevant_policies]
            },
            'records': {
                'total_records': len(self.data_records),
                'expired_records': expired_records,
                'legal_hold_records': legal_hold_records,
                'by_policy': dict(records_by_policy),
                'by_classification': defaultdict(int)
            },
            'audit_events': {
                'total_events': len(relevant_events),
                'by_type': dict(event_summary),
                'recent_events': [e.to_dict() for e in relevant_events[-20:]]
            },
            'compliance_status': {
                'policies_with_framework': len([p for p in relevant_policies if p.compliance_frameworks]),
                'records_under_legal_hold': legal_hold_records,
                'overdue_actions': expired_records
            }
        }
        
        # Count by framework and classification
        for policy in relevant_policies:
            for framework_val in policy.compliance_frameworks:
                report['policies']['by_framework'][framework_val.value] += 1
        
        for record in self.data_records.values():
            report['records']['by_classification'][record.classification.value] += 1
        
        return report
    
    def get_retention_status(self) -> Dict[str, Any]:
        """Get overall retention system status"""
        now = datetime.utcnow()
        
        # Calculate statistics
        total_records = len(self.data_records)
        expired_records = sum(1 for r in self.data_records.values() if r.expiry_date <= now)
        legal_hold_records = sum(1 for r in self.data_records.values() if r.legal_hold)
        
        # Records by status
        archive_status_counts = defaultdict(int)
        for record in self.data_records.values():
            archive_status_counts[record.archive_status.value] += 1
        
        # Records expiring soon (next 30 days)
        soon_cutoff = now + timedelta(days=30)
        expiring_soon = sum(1 for r in self.data_records.values() 
                           if now < r.expiry_date <= soon_cutoff and not r.legal_hold)
        
        # Total managed data size
        total_size = sum(r.size_bytes for r in self.data_records.values())
        
        return {
            'system_status': 'active',
            'total_policies': len(self.retention_policies),
            'active_policies': len([p for p in self.retention_policies.values() if p.enabled]),
            'records': {
                'total': total_records,
                'expired': expired_records,
                'legal_hold': legal_hold_records,
                'expiring_soon': expiring_soon,
                'by_archive_status': dict(archive_status_counts)
            },
            'data_volume': {
                'total_bytes': total_size,
                'total_mb': round(total_size / (1024 * 1024), 2),
                'total_gb': round(total_size / (1024 * 1024 * 1024), 2)
            },
            'audit_events_count': len(self.audit_events),
            'archive_jobs_active': len(self.archive_manager.active_jobs),
            'last_updated': now.isoformat()
        }


# Global retention system instance
_retention_system = None

def get_retention_system(base_path: str = ".", database_path: str = "retention.db") -> RetentionArchivalSystem:
    """Get or create the global retention system instance"""
    global _retention_system
    if _retention_system is None:
        _retention_system = RetentionArchivalSystem(base_path, database_path)
    return _retention_system


def main():
    """Command line interface for data retention and archival"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 Data Retention & Archival System")
    parser.add_argument('--path', default='.', help='Base path for data management')
    parser.add_argument('--scan', action='store_true', help='Scan directory and register files')
    parser.add_argument('--process-expired', action='store_true', help='Process expired records')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no changes)')
    parser.add_argument('--status', action='store_true', help='Show system status')
    parser.add_argument('--compliance-report', help='Generate compliance report for framework')
    parser.add_argument('--legal-hold', nargs=2, metavar=('RECORD_IDS', 'REASON'), 
                       help='Apply legal hold to records')
    parser.add_argument('--remove-hold', help='Remove legal hold from record IDs')
    
    args = parser.parse_args()
    
    retention_system = get_retention_system(args.path)
    
    try:
        if args.scan:
            print("Scanning directory for data records...")
            result = retention_system.scan_directory()
            print(json.dumps(result, indent=2))
        
        elif args.process_expired:
            print(f"Processing expired records (dry_run={args.dry_run})...")
            result = retention_system.process_expired_records(dry_run=args.dry_run)
            print(json.dumps(result, indent=2, default=str))
        
        elif args.status:
            status = retention_system.get_retention_status()
            print(json.dumps(status, indent=2))
        
        elif args.compliance_report:
            try:
                framework = ComplianceFramework(args.compliance_report)
                report = retention_system.get_compliance_report(framework)
                print(json.dumps(report, indent=2, default=str))
            except ValueError:
                print(f"Invalid compliance framework: {args.compliance_report}")
                print("Available frameworks:", [f.value for f in ComplianceFramework])
        
        elif args.legal_hold:
            record_ids = args.legal_hold[0].split(',')
            reason = args.legal_hold[1]
            result = retention_system.apply_legal_hold(record_ids, reason)
            print(f"Legal hold applied to {result['applied_count']} records")
        
        elif args.remove_hold:
            record_ids = args.remove_hold.split(',')
            result = retention_system.remove_legal_hold(record_ids)
            print(f"Legal hold removed from {result['removed_count']} records")
        
        else:
            print("JARVIS-MK42 Data Retention & Archival System")
            print("Use --help for available options")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
