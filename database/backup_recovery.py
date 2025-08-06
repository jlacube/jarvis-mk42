#!/usr/bin/env python3
"""
JARVIS-MK42 Backup & Recovery System
===================================

This module provides comprehensive backup and recovery capabilities including:
- Automated database backups with scheduling
- Full system backups and incremental backups
- Point-in-time recovery capabilities
- Backup verification and integrity checking
- Multi-destination backup support (local, cloud)
- Backup retention policies and cleanup
- Recovery testing and validation
- Backup monitoring and alerting
"""

import os
import sys
import json
import gzip
import shutil
import sqlite3
import tempfile
import threading
import schedule
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict, namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import time

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger

logger = get_logger(__name__)

try:
    import boto3
    HAS_AWS = True
except ImportError:
    HAS_AWS = False
    logger.info("boto3 not available - AWS S3 backup disabled")

try:
    from azure.storage.blob import BlobServiceClient
    HAS_AZURE = True
except ImportError:
    HAS_AZURE = False
    logger.info("azure-storage-blob not available - Azure backup disabled")


class BackupType(Enum):
    """Types of backups"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    DATABASE_ONLY = "database_only"
    CONFIGURATION = "configuration"


class BackupStatus(Enum):
    """Backup operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    CORRUPTED = "corrupted"


class BackupDestination(Enum):
    """Backup destination types"""
    LOCAL = "local"
    AWS_S3 = "aws_s3"
    AZURE_BLOB = "azure_blob"
    FTP = "ftp"
    NETWORK_SHARE = "network_share"


@dataclass
class BackupConfiguration:
    """Backup configuration settings"""
    enabled: bool = True
    backup_directory: str = "backups"
    max_backups_to_keep: int = 30
    compression_enabled: bool = True
    encryption_enabled: bool = False
    encryption_key: Optional[str] = None
    
    # Scheduling
    daily_backup_time: str = "02:00"
    weekly_backup_day: str = "sunday"
    monthly_backup_day: int = 1
    
    # Retention policies
    daily_retention_days: int = 7
    weekly_retention_weeks: int = 4
    monthly_retention_months: int = 12
    yearly_retention_years: int = 3
    
    # Destinations
    destinations: List[Dict[str, Any]] = field(default_factory=lambda: [
        {"type": "local", "path": "backups", "enabled": True}
    ])
    
    # Verification
    verify_backups: bool = True
    verification_percentage: float = 100.0  # Percentage of backups to verify
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'enabled': self.enabled,
            'backup_directory': self.backup_directory,
            'max_backups_to_keep': self.max_backups_to_keep,
            'compression_enabled': self.compression_enabled,
            'encryption_enabled': self.encryption_enabled,
            'daily_backup_time': self.daily_backup_time,
            'weekly_backup_day': self.weekly_backup_day,
            'monthly_backup_day': self.monthly_backup_day,
            'daily_retention_days': self.daily_retention_days,
            'weekly_retention_weeks': self.weekly_retention_weeks,
            'monthly_retention_months': self.monthly_retention_months,
            'yearly_retention_years': self.yearly_retention_years,
            'destinations': self.destinations,
            'verify_backups': self.verify_backups,
            'verification_percentage': self.verification_percentage
        }


@dataclass
class BackupMetadata:
    """Metadata for a backup"""
    backup_id: str
    backup_type: BackupType
    created_at: datetime
    completed_at: Optional[datetime]
    status: BackupStatus
    source_paths: List[str]
    backup_path: str
    compressed_size: int
    uncompressed_size: int
    checksum: str
    compression_ratio: float
    database_version: Optional[str] = None
    notes: str = ""
    verification_status: Optional[bool] = None
    verification_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'backup_id': self.backup_id,
            'backup_type': self.backup_type.value,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'status': self.status.value,
            'source_paths': self.source_paths,
            'backup_path': self.backup_path,
            'compressed_size': self.compressed_size,
            'compressed_size_mb': round(self.compressed_size / (1024 * 1024), 2),
            'uncompressed_size': self.uncompressed_size,
            'uncompressed_size_mb': round(self.uncompressed_size / (1024 * 1024), 2),
            'checksum': self.checksum,
            'compression_ratio': self.compression_ratio,
            'database_version': self.database_version,
            'notes': self.notes,
            'verification_status': self.verification_status,
            'verification_time': self.verification_time.isoformat() if self.verification_time else None
        }


@dataclass
class RecoveryPoint:
    """Point-in-time recovery point"""
    timestamp: datetime
    backup_id: str
    database_size: int
    transaction_count: int
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'backup_id': self.backup_id,
            'database_size': self.database_size,
            'transaction_count': self.transaction_count,
            'description': self.description
        }


class BackupDestinationManager:
    """Manages different backup destinations"""
    
    def __init__(self):
        self.destinations = {}
    
    def register_destination(self, dest_type: BackupDestination, config: Dict[str, Any]):
        """Register a backup destination"""
        self.destinations[dest_type] = config
        logger.info("Registered backup destination: %s", dest_type.value)
    
    def upload_backup(self, dest_type: BackupDestination, local_path: Path, remote_path: str) -> bool:
        """Upload backup to destination"""
        try:
            if dest_type == BackupDestination.LOCAL:
                return self._upload_local(local_path, remote_path)
            elif dest_type == BackupDestination.AWS_S3 and HAS_AWS:
                return self._upload_s3(local_path, remote_path)
            elif dest_type == BackupDestination.AZURE_BLOB and HAS_AZURE:
                return self._upload_azure(local_path, remote_path)
            else:
                logger.error("Unsupported or unavailable destination: %s", dest_type)
                return False
        except Exception as e:
            logger.error("Failed to upload backup to %s: %s", dest_type, e)
            return False
    
    def _upload_local(self, local_path: Path, remote_path: str) -> bool:
        """Upload to local destination"""
        dest_path = Path(remote_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dest_path)
        logger.info("Backup uploaded to local destination: %s", dest_path)
        return True
    
    def _upload_s3(self, local_path: Path, remote_path: str) -> bool:
        """Upload to AWS S3"""
        if not HAS_AWS:
            return False
        
        config = self.destinations.get(BackupDestination.AWS_S3, {})
        bucket = config.get('bucket')
        if not bucket:
            logger.error("AWS S3 bucket not configured")
            return False
        
        s3_client = boto3.client('s3')
        s3_client.upload_file(str(local_path), bucket, remote_path)
        logger.info("Backup uploaded to S3: s3://%s/%s", bucket, remote_path)
        return True
    
    def _upload_azure(self, local_path: Path, remote_path: str) -> bool:
        """Upload to Azure Blob Storage"""
        if not HAS_AZURE:
            return False
        
        config = self.destinations.get(BackupDestination.AZURE_BLOB, {})
        connection_string = config.get('connection_string')
        container = config.get('container')
        
        if not connection_string or not container:
            logger.error("Azure Blob Storage not properly configured")
            return False
        
        blob_service = BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service.get_blob_client(container=container, blob=remote_path)
        
        with open(local_path, 'rb') as data:
            blob_client.upload_blob(data, overwrite=True)
        
        logger.info("Backup uploaded to Azure Blob: %s/%s", container, remote_path)
        return True


class DatabaseBackupManager:
    """Specialized manager for database backups"""
    
    def __init__(self, database_path: str = "jarvis.db"):
        self.database_path = Path(database_path)
        
    def create_database_backup(self, backup_path: Path) -> Tuple[int, str]:
        """
        Create a database backup using SQLite's backup API.
        
        Returns:
            Tuple of (backup_size, checksum)
        """
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database file not found: {self.database_path}")
        
        # Create backup directory
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use SQLite's backup API for consistent backups
        source_conn = sqlite3.connect(str(self.database_path))
        backup_conn = sqlite3.connect(str(backup_path))
        
        try:
            # Perform the backup
            source_conn.backup(backup_conn)
            backup_conn.close()
            source_conn.close()
            
            # Get backup size and checksum
            backup_size = backup_path.stat().st_size
            checksum = self._calculate_file_checksum(backup_path)
            
            logger.info("Database backup created: %s (%d bytes)", backup_path.name, backup_size)
            return backup_size, checksum
            
        except Exception as e:
            if backup_conn:
                backup_conn.close()
            if source_conn:
                source_conn.close()
            raise e
    
    def verify_database_backup(self, backup_path: Path) -> bool:
        """Verify the integrity of a database backup"""
        try:
            # Try to connect to the backup database
            conn = sqlite3.connect(str(backup_path))
            
            # Perform integrity check
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()
            
            is_valid = result and result[0] == 'ok'
            logger.info("Database backup verification: %s (%s)", 
                       backup_path.name, "PASS" if is_valid else "FAIL")
            return is_valid
            
        except Exception as e:
            logger.error("Database backup verification failed: %s", e)
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information for backup metadata"""
        try:
            conn = sqlite3.connect(str(self.database_path))
            
            # Get database stats
            cursor = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            
            cursor = conn.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            
            cursor = conn.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            # Get SQLite version
            cursor = conn.execute("SELECT sqlite_version()")
            sqlite_version = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'table_count': table_count,
                'page_count': page_count,
                'page_size': page_size,
                'database_size': page_count * page_size,
                'sqlite_version': sqlite_version,
                'file_size': self.database_path.stat().st_size
            }
            
        except Exception as e:
            logger.error("Failed to get database info: %s", e)
            return {}
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file"""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()


class BackupRecoverySystem:
    """
    Main backup and recovery system.
    
    Provides comprehensive backup and recovery capabilities including
    automated scheduling, verification, and multi-destination support.
    """
    
    def __init__(self, base_path: str = ".", config: Optional[BackupConfiguration] = None):
        self.base_path = Path(base_path).resolve()
        self.config = config or BackupConfiguration()
        self.backup_directory = self.base_path / self.config.backup_directory
        self.backup_directory.mkdir(exist_ok=True)
        
        self.destination_manager = BackupDestinationManager()
        self.db_manager = DatabaseBackupManager()
        self.metadata_file = self.backup_directory / "backup_metadata.json"
        self.recovery_points_file = self.backup_directory / "recovery_points.json"
        
        self.backup_metadata: Dict[str, BackupMetadata] = {}
        self.recovery_points: List[RecoveryPoint] = []
        self.lock = threading.RLock()
        self._scheduler_running = False
        
        # Load existing metadata
        self._load_metadata()
        self._setup_destinations()
        
        logger.info("Backup & Recovery System initialized for path: %s", self.base_path)
    
    def _load_metadata(self):
        """Load backup metadata from file"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    
                for backup_id, metadata_dict in data.items():
                    # Convert string dates back to datetime objects
                    metadata_dict['created_at'] = datetime.fromisoformat(metadata_dict['created_at'])
                    if metadata_dict.get('completed_at'):
                        metadata_dict['completed_at'] = datetime.fromisoformat(metadata_dict['completed_at'])
                    if metadata_dict.get('verification_time'):
                        metadata_dict['verification_time'] = datetime.fromisoformat(metadata_dict['verification_time'])
                    
                    # Convert enums
                    metadata_dict['backup_type'] = BackupType(metadata_dict['backup_type'])
                    metadata_dict['status'] = BackupStatus(metadata_dict['status'])
                    
                    self.backup_metadata[backup_id] = BackupMetadata(**metadata_dict)
                
                logger.info("Loaded metadata for %d backups", len(self.backup_metadata))
            
            # Load recovery points
            if self.recovery_points_file.exists():
                with open(self.recovery_points_file, 'r') as f:
                    data = json.load(f)
                    
                self.recovery_points = [
                    RecoveryPoint(
                        timestamp=datetime.fromisoformat(rp['timestamp']),
                        backup_id=rp['backup_id'],
                        database_size=rp['database_size'],
                        transaction_count=rp['transaction_count'],
                        description=rp['description']
                    ) for rp in data
                ]
                
                logger.info("Loaded %d recovery points", len(self.recovery_points))
                
        except Exception as e:
            logger.error("Error loading backup metadata: %s", e)
    
    def _save_metadata(self):
        """Save backup metadata to file"""
        try:
            with self.lock:
                # Prepare metadata for JSON serialization
                metadata_dict = {}
                for backup_id, metadata in self.backup_metadata.items():
                    metadata_dict[backup_id] = metadata.to_dict()
                
                with open(self.metadata_file, 'w') as f:
                    json.dump(metadata_dict, f, indent=2)
                
                # Save recovery points
                recovery_points_dict = [rp.to_dict() for rp in self.recovery_points]
                with open(self.recovery_points_file, 'w') as f:
                    json.dump(recovery_points_dict, f, indent=2)
                
        except Exception as e:
            logger.error("Error saving backup metadata: %s", e)
    
    def _setup_destinations(self):
        """Setup backup destinations from configuration"""
        for dest_config in self.config.destinations:
            if not dest_config.get('enabled', True):
                continue
            
            dest_type = BackupDestination(dest_config['type'])
            self.destination_manager.register_destination(dest_type, dest_config)
    
    def create_backup(self, backup_type: BackupType = BackupType.FULL, 
                     sources: Optional[List[str]] = None) -> str:
        """
        Create a new backup.
        
        Args:
            backup_type: Type of backup to create
            sources: List of source paths to backup (None for default)
            
        Returns:
            Backup ID
        """
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{backup_type.value}"
        
        logger.info("Creating backup: %s (%s)", backup_id, backup_type.value)
        
        # Default sources
        if sources is None:
            sources = self._get_default_backup_sources(backup_type)
        
        # Create backup metadata
        metadata = BackupMetadata(
            backup_id=backup_id,
            backup_type=backup_type,
            created_at=datetime.now(),
            completed_at=None,
            status=BackupStatus.IN_PROGRESS,
            source_paths=sources,
            backup_path="",
            compressed_size=0,
            uncompressed_size=0,
            checksum="",
            compression_ratio=0.0
        )
        
        with self.lock:
            self.backup_metadata[backup_id] = metadata
        
        try:
            # Create the backup
            if backup_type == BackupType.DATABASE_ONLY:
                backup_path, size, checksum = self._create_database_backup(backup_id)
            else:
                backup_path, size, checksum = self._create_file_backup(backup_id, sources)
            
            # Update metadata
            metadata.backup_path = str(backup_path)
            metadata.compressed_size = size
            metadata.uncompressed_size = self._calculate_uncompressed_size(sources)
            metadata.checksum = checksum
            metadata.compression_ratio = (1 - (size / metadata.uncompressed_size)) if metadata.uncompressed_size > 0 else 0
            metadata.completed_at = datetime.now()
            metadata.status = BackupStatus.COMPLETED
            
            # Get database info for database backups
            if backup_type == BackupType.DATABASE_ONLY:
                db_info = self.db_manager.get_database_info()
                metadata.database_version = db_info.get('sqlite_version')
            
            # Save metadata
            self._save_metadata()
            
            # Verify backup if configured
            if self.config.verify_backups:
                self._verify_backup_async(backup_id)
            
            # Upload to destinations
            self._upload_to_destinations(backup_path, backup_id)
            
            # Create recovery point
            if backup_type in [BackupType.FULL, BackupType.DATABASE_ONLY]:
                self._create_recovery_point(backup_id)
            
            logger.info("Backup created successfully: %s", backup_id)
            return backup_id
            
        except Exception as e:
            metadata.status = BackupStatus.FAILED
            metadata.notes = str(e)
            self._save_metadata()
            logger.error("Backup creation failed: %s", e)
            raise
    
    def _get_default_backup_sources(self, backup_type: BackupType) -> List[str]:
        """Get default source paths for backup type"""
        sources = []
        
        if backup_type == BackupType.DATABASE_ONLY:
            sources = ["jarvis.db"]
        elif backup_type == BackupType.CONFIGURATION:
            sources = ["config.py", "*.yaml", "*.yml", "*.json", ".env"]
        else:
            # Full backup - exclude common non-essential directories
            exclude_patterns = {
                "__pycache__", ".git", ".pytest_cache", "node_modules",
                ".vscode", ".idea", "*.pyc", "*.pyo", "logs/*.log"
            }
            # Include all files except excluded ones
            sources = [str(self.base_path)]
        
        return sources
    
    def _create_database_backup(self, backup_id: str) -> Tuple[Path, int, str]:
        """Create a database-only backup"""
        backup_filename = f"{backup_id}.db"
        if self.config.compression_enabled:
            backup_filename += ".gz"
        
        backup_path = self.backup_directory / backup_filename
        
        # Create database backup
        temp_db_path = backup_path.with_suffix('.tmp.db')
        size, checksum = self.db_manager.create_database_backup(temp_db_path)
        
        # Compress if enabled
        if self.config.compression_enabled:
            with open(temp_db_path, 'rb') as src, gzip.open(backup_path, 'wb') as dst:
                shutil.copyfileobj(src, dst)
            temp_db_path.unlink()  # Remove temporary file
            size = backup_path.stat().st_size
            
            # Recalculate checksum for compressed file
            hasher = hashlib.sha256()
            with open(backup_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            checksum = hasher.hexdigest()
        else:
            shutil.move(temp_db_path, backup_path)
        
        return backup_path, size, checksum
    
    def _create_file_backup(self, backup_id: str, sources: List[str]) -> Tuple[Path, int, str]:
        """Create a file-based backup"""
        backup_filename = f"{backup_id}.tar"
        if self.config.compression_enabled:
            backup_filename += ".gz"
        
        backup_path = self.backup_directory / backup_filename
        
        import tarfile
        
        # Create tar archive
        mode = "w:gz" if self.config.compression_enabled else "w"
        with tarfile.open(backup_path, mode) as tar:
            for source in sources:
                source_path = self.base_path / source
                if source_path.exists():
                    if source_path.is_file():
                        tar.add(source_path, arcname=source)
                    elif source_path.is_dir():
                        tar.add(source_path, arcname=source, recursive=True)
        
        # Get size and checksum
        size = backup_path.stat().st_size
        hasher = hashlib.sha256()
        with open(backup_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        checksum = hasher.hexdigest()
        
        return backup_path, size, checksum
    
    def _calculate_uncompressed_size(self, sources: List[str]) -> int:
        """Calculate the total uncompressed size of source files"""
        total_size = 0
        
        for source in sources:
            source_path = self.base_path / source
            if source_path.exists():
                if source_path.is_file():
                    total_size += source_path.stat().st_size
                elif source_path.is_dir():
                    for root, dirs, files in os.walk(source_path):
                        for file in files:
                            file_path = Path(root) / file
                            try:
                                total_size += file_path.stat().st_size
                            except (OSError, PermissionError):
                                pass
        
        return total_size
    
    def _verify_backup_async(self, backup_id: str):
        """Verify backup in a separate thread"""
        def verify():
            try:
                is_valid = self.verify_backup(backup_id)
                with self.lock:
                    metadata = self.backup_metadata.get(backup_id)
                    if metadata:
                        metadata.verification_status = is_valid
                        metadata.verification_time = datetime.now()
                        if is_valid:
                            metadata.status = BackupStatus.VERIFIED
                        else:
                            metadata.status = BackupStatus.CORRUPTED
                        self._save_metadata()
            except Exception as e:
                logger.error("Backup verification failed for %s: %s", backup_id, e)
        
        threading.Thread(target=verify, daemon=True).start()
    
    def _upload_to_destinations(self, backup_path: Path, backup_id: str):
        """Upload backup to configured destinations"""
        for dest_config in self.config.destinations:
            if not dest_config.get('enabled', True):
                continue
            
            try:
                dest_type = BackupDestination(dest_config['type'])
                remote_path = f"{backup_id}/{backup_path.name}"
                
                success = self.destination_manager.upload_backup(dest_type, backup_path, remote_path)
                if success:
                    logger.info("Backup uploaded to %s", dest_type.value)
                else:
                    logger.error("Failed to upload backup to %s", dest_type.value)
            except Exception as e:
                logger.error("Error uploading to destination %s: %s", dest_config.get('type'), e)
    
    def _create_recovery_point(self, backup_id: str):
        """Create a recovery point for the backup"""
        db_info = self.db_manager.get_database_info()
        
        recovery_point = RecoveryPoint(
            timestamp=datetime.now(),
            backup_id=backup_id,
            database_size=db_info.get('database_size', 0),
            transaction_count=db_info.get('table_count', 0),  # Approximation
            description=f"Auto-generated recovery point for {backup_id}"
        )
        
        with self.lock:
            self.recovery_points.append(recovery_point)
            # Keep only the last 100 recovery points
            self.recovery_points = self.recovery_points[-100:]
        
        self._save_metadata()
    
    def verify_backup(self, backup_id: str) -> bool:
        """
        Verify the integrity of a backup.
        
        Args:
            backup_id: ID of the backup to verify
            
        Returns:
            True if backup is valid, False otherwise
        """
        metadata = self.backup_metadata.get(backup_id)
        if not metadata:
            logger.error("Backup not found: %s", backup_id)
            return False
        
        backup_path = Path(metadata.backup_path)
        if not backup_path.exists():
            logger.error("Backup file not found: %s", backup_path)
            return False
        
        try:
            # Verify checksum
            hasher = hashlib.sha256()
            with open(backup_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            
            calculated_checksum = hasher.hexdigest()
            checksum_valid = calculated_checksum == metadata.checksum
            
            if not checksum_valid:
                logger.error("Checksum verification failed for backup %s", backup_id)
                return False
            
            # Additional verification based on backup type
            if metadata.backup_type == BackupType.DATABASE_ONLY:
                # For database backups, try to verify the database structure
                if backup_path.suffix == '.gz':
                    # Decompress temporarily for verification
                    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
                        with gzip.open(backup_path, 'rb') as gz_file:
                            shutil.copyfileobj(gz_file, tmp_file)
                        tmp_path = Path(tmp_file.name)
                    
                    is_valid = self.db_manager.verify_database_backup(tmp_path)
                    tmp_path.unlink()  # Clean up
                    return is_valid
                else:
                    return self.db_manager.verify_database_backup(backup_path)
            
            # For file backups, basic existence and checksum verification is sufficient
            return True
            
        except Exception as e:
            logger.error("Error verifying backup %s: %s", backup_id, e)
            return False
    
    def restore_backup(self, backup_id: str, restore_path: Optional[str] = None) -> bool:
        """
        Restore a backup.
        
        Args:
            backup_id: ID of the backup to restore
            restore_path: Path to restore to (None for original location)
            
        Returns:
            True if restoration was successful, False otherwise
        """
        metadata = self.backup_metadata.get(backup_id)
        if not metadata:
            logger.error("Backup not found: %s", backup_id)
            return False
        
        backup_path = Path(metadata.backup_path)
        if not backup_path.exists():
            logger.error("Backup file not found: %s", backup_path)
            return False
        
        logger.info("Restoring backup: %s", backup_id)
        
        try:
            if metadata.backup_type == BackupType.DATABASE_ONLY:
                return self._restore_database_backup(backup_path, restore_path)
            else:
                return self._restore_file_backup(backup_path, restore_path)
                
        except Exception as e:
            logger.error("Error restoring backup %s: %s", backup_id, e)
            return False
    
    def _restore_database_backup(self, backup_path: Path, restore_path: Optional[str] = None) -> bool:
        """Restore a database backup"""
        target_path = Path(restore_path) if restore_path else self.base_path / "jarvis.db"
        
        # Create backup of current database if it exists
        if target_path.exists():
            backup_current = target_path.with_suffix('.db.backup')
            shutil.copy2(target_path, backup_current)
            logger.info("Current database backed up to: %s", backup_current)
        
        try:
            if backup_path.suffix == '.gz':
                # Decompress the backup
                with gzip.open(backup_path, 'rb') as src, open(target_path, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
            else:
                shutil.copy2(backup_path, target_path)
            
            # Verify the restored database
            if self.db_manager.verify_database_backup(target_path):
                logger.info("Database restoration completed successfully")
                return True
            else:
                logger.error("Restored database failed verification")
                return False
                
        except Exception as e:
            logger.error("Database restoration failed: %s", e)
            return False
    
    def _restore_file_backup(self, backup_path: Path, restore_path: Optional[str] = None) -> bool:
        """Restore a file backup"""
        target_path = Path(restore_path) if restore_path else self.base_path
        
        import tarfile
        
        try:
            with tarfile.open(backup_path, 'r:*') as tar:
                tar.extractall(path=target_path)
            
            logger.info("File restoration completed successfully")
            return True
            
        except Exception as e:
            logger.error("File restoration failed: %s", e)
            return False
    
    def list_backups(self, backup_type: Optional[BackupType] = None) -> List[Dict[str, Any]]:
        """
        List available backups.
        
        Args:
            backup_type: Filter by backup type (None for all)
            
        Returns:
            List of backup information dictionaries
        """
        backups = []
        
        with self.lock:
            for backup_id, metadata in self.backup_metadata.items():
                if backup_type is None or metadata.backup_type == backup_type:
                    backup_info = metadata.to_dict()
                    backup_info['exists'] = Path(metadata.backup_path).exists()
                    backups.append(backup_info)
        
        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        return backups
    
    def cleanup_old_backups(self) -> Dict[str, Any]:
        """
        Clean up old backups according to retention policy.
        
        Returns:
            Dictionary with cleanup results
        """
        logger.info("Starting backup cleanup...")
        
        deleted_backups = []
        total_space_freed = 0
        
        with self.lock:
            backups_to_delete = self._get_backups_to_delete()
            
            for backup_id in backups_to_delete:
                metadata = self.backup_metadata.get(backup_id)
                if metadata:
                    backup_path = Path(metadata.backup_path)
                    if backup_path.exists():
                        try:
                            space_freed = backup_path.stat().st_size
                            backup_path.unlink()
                            total_space_freed += space_freed
                            deleted_backups.append({
                                'backup_id': backup_id,
                                'size_freed': space_freed,
                                'created_at': metadata.created_at.isoformat()
                            })
                            logger.info("Deleted old backup: %s (%.2f MB)", 
                                       backup_id, space_freed / (1024 * 1024))
                        except Exception as e:
                            logger.error("Failed to delete backup %s: %s", backup_id, e)
                    
                    # Remove from metadata
                    del self.backup_metadata[backup_id]
            
            # Update recovery points - remove references to deleted backups
            self.recovery_points = [
                rp for rp in self.recovery_points 
                if rp.backup_id not in backups_to_delete
            ]
            
            self._save_metadata()
        
        result = {
            'deleted_count': len(deleted_backups),
            'space_freed': total_space_freed,
            'space_freed_mb': round(total_space_freed / (1024 * 1024), 2),
            'deleted_backups': deleted_backups
        }
        
        logger.info("Backup cleanup completed: %d backups deleted, %.2f MB freed",
                   len(deleted_backups), result['space_freed_mb'])
        
        return result
    
    def _get_backups_to_delete(self) -> List[str]:
        """Determine which backups should be deleted based on retention policy"""
        backups_to_delete = []
        
        # Group backups by type and date
        backups_by_date = defaultdict(list)
        
        for backup_id, metadata in self.backup_metadata.items():
            if metadata.status == BackupStatus.COMPLETED:
                date_key = metadata.created_at.date()
                backups_by_date[date_key].append(backup_id)
        
        # Apply retention policy
        today = datetime.now().date()
        
        for date_key, backup_ids in backups_by_date.items():
            days_old = (today - date_key).days
            
            # Keep all backups within daily retention period
            if days_old <= self.config.daily_retention_days:
                continue
            
            # For older backups, apply more aggressive retention
            if days_old <= self.config.weekly_retention_weeks * 7:
                # Keep only one backup per week
                if len(backup_ids) > 1:
                    # Keep the first backup of the week, delete others
                    backups_to_delete.extend(backup_ids[1:])
            elif days_old <= self.config.monthly_retention_months * 30:
                # Keep only one backup per month
                if len(backup_ids) > 1:
                    backups_to_delete.extend(backup_ids[1:])
            elif days_old > self.config.yearly_retention_years * 365:
                # Delete all backups older than yearly retention
                backups_to_delete.extend(backup_ids)
        
        # Also enforce maximum backup count
        all_backup_ids = list(self.backup_metadata.keys())
        if len(all_backup_ids) > self.config.max_backups_to_keep:
            # Sort by date and keep only the newest ones
            sorted_backups = sorted(
                [(bid, self.backup_metadata[bid].created_at) for bid in all_backup_ids],
                key=lambda x: x[1],
                reverse=True
            )
            
            old_backups = [bid for bid, _ in sorted_backups[self.config.max_backups_to_keep:]]
            backups_to_delete.extend(old_backups)
        
        return list(set(backups_to_delete))  # Remove duplicates
    
    def start_scheduler(self):
        """Start the backup scheduler"""
        if self._scheduler_running:
            logger.warning("Backup scheduler is already running")
            return
        
        if not self.config.enabled:
            logger.info("Backup system is disabled - scheduler not started")
            return
        
        # Schedule daily backups
        schedule.every().day.at(self.config.daily_backup_time).do(
            self._scheduled_backup, BackupType.DATABASE_ONLY
        )
        
        # Schedule weekly full backups
        getattr(schedule.every(), self.config.weekly_backup_day.lower()).at(
            self.config.daily_backup_time
        ).do(self._scheduled_backup, BackupType.FULL)
        
        # Schedule monthly cleanup
        schedule.every().month.do(self.cleanup_old_backups)
        
        self._scheduler_running = True
        
        def run_scheduler():
            while self._scheduler_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        logger.info("Backup scheduler started")
    
    def stop_scheduler(self):
        """Stop the backup scheduler"""
        self._scheduler_running = False
        schedule.clear()
        logger.info("Backup scheduler stopped")
    
    def _scheduled_backup(self, backup_type: BackupType):
        """Perform a scheduled backup"""
        try:
            backup_id = self.create_backup(backup_type)
            logger.info("Scheduled backup completed: %s", backup_id)
        except Exception as e:
            logger.error("Scheduled backup failed: %s", e)
    
    def get_backup_status(self) -> Dict[str, Any]:
        """Get comprehensive backup system status"""
        with self.lock:
            total_backups = len(self.backup_metadata)
            successful_backups = len([m for m in self.backup_metadata.values() 
                                    if m.status == BackupStatus.COMPLETED])
            failed_backups = len([m for m in self.backup_metadata.values() 
                                if m.status == BackupStatus.FAILED])
            
            total_backup_size = sum(m.compressed_size for m in self.backup_metadata.values())
            
            # Get latest backup info
            latest_backup = None
            if self.backup_metadata:
                latest_backup = max(self.backup_metadata.values(), 
                                  key=lambda x: x.created_at)
            
            # Check disk usage
            backup_dir_size = sum(f.stat().st_size for f in self.backup_directory.glob('**/*') 
                                 if f.is_file())
            
            return {
                'system_enabled': self.config.enabled,
                'scheduler_running': self._scheduler_running,
                'total_backups': total_backups,
                'successful_backups': successful_backups,
                'failed_backups': failed_backups,
                'success_rate': (successful_backups / total_backups * 100) if total_backups > 0 else 0,
                'total_backup_size': total_backup_size,
                'total_backup_size_mb': round(total_backup_size / (1024 * 1024), 2),
                'backup_directory_size': backup_dir_size,
                'backup_directory_size_mb': round(backup_dir_size / (1024 * 1024), 2),
                'latest_backup': {
                    'backup_id': latest_backup.backup_id,
                    'created_at': latest_backup.created_at.isoformat(),
                    'status': latest_backup.status.value,
                    'type': latest_backup.backup_type.value
                } if latest_backup else None,
                'recovery_points_count': len(self.recovery_points),
                'destinations_configured': len(self.config.destinations),
                'retention_policy': {
                    'daily_retention_days': self.config.daily_retention_days,
                    'weekly_retention_weeks': self.config.weekly_retention_weeks,
                    'monthly_retention_months': self.config.monthly_retention_months,
                    'max_backups': self.config.max_backups_to_keep
                }
            }
    
    def get_recovery_points(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get available recovery points"""
        with self.lock:
            points = sorted(self.recovery_points, key=lambda x: x.timestamp, reverse=True)
            return [point.to_dict() for point in points[:limit]]
    
    def update_configuration(self, config: BackupConfiguration):
        """Update backup configuration"""
        with self.lock:
            self.config = config
            self._setup_destinations()
        logger.info("Backup configuration updated")


# Global backup system instance
_backup_system = None

def get_backup_system(base_path: str = ".", config: Optional[BackupConfiguration] = None) -> BackupRecoverySystem:
    """Get or create the global backup system instance"""
    global _backup_system
    if _backup_system is None:
        _backup_system = BackupRecoverySystem(base_path, config)
    return _backup_system


def main():
    """Command line interface for backup and recovery"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 Backup & Recovery System")
    parser.add_argument('--path', default='.', help='Base path for backup operations')
    parser.add_argument('--backup', choices=['full', 'incremental', 'database', 'config'], 
                       help='Create backup of specified type')
    parser.add_argument('--list', action='store_true', help='List available backups')
    parser.add_argument('--restore', help='Restore backup by ID')
    parser.add_argument('--verify', help='Verify backup by ID')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old backups')
    parser.add_argument('--status', action='store_true', help='Show backup system status')
    parser.add_argument('--recovery-points', action='store_true', help='List recovery points')
    parser.add_argument('--start-scheduler', action='store_true', help='Start backup scheduler')
    
    args = parser.parse_args()
    
    backup_system = get_backup_system(args.path)
    
    try:
        if args.backup:
            backup_type_map = {
                'full': BackupType.FULL,
                'incremental': BackupType.INCREMENTAL,
                'database': BackupType.DATABASE_ONLY,
                'config': BackupType.CONFIGURATION
            }
            backup_type = backup_type_map[args.backup]
            backup_id = backup_system.create_backup(backup_type)
            print(f"Backup created: {backup_id}")
        
        elif args.list:
            backups = backup_system.list_backups()
            print(f"Available backups ({len(backups)}):")
            for backup in backups:
                print(f"  {backup['backup_id']}: {backup['backup_type']} "
                      f"({backup['status']}) - {backup['created_at']}")
        
        elif args.restore:
            success = backup_system.restore_backup(args.restore)
            print(f"Restore {'successful' if success else 'failed'}")
        
        elif args.verify:
            is_valid = backup_system.verify_backup(args.verify)
            print(f"Backup verification: {'PASS' if is_valid else 'FAIL'}")
        
        elif args.cleanup:
            result = backup_system.cleanup_old_backups()
            print(f"Cleanup completed: {result['deleted_count']} backups deleted, "
                  f"{result['space_freed_mb']} MB freed")
        
        elif args.status:
            status = backup_system.get_backup_status()
            print(json.dumps(status, indent=2))
        
        elif args.recovery_points:
            points = backup_system.get_recovery_points()
            print(f"Recovery points ({len(points)}):")
            for point in points:
                print(f"  {point['timestamp']}: {point['description']}")
        
        elif args.start_scheduler:
            backup_system.start_scheduler()
            print("Backup scheduler started")
            
        else:
            print("JARVIS-MK42 Backup & Recovery System")
            print("Use --help for available options")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
