#!/usr/bin/env python3
"""
JARVIS-MK42 Storage Management System
===================================

This module provides comprehensive storage management capabilities including:
- File compression and decompression
- Automated cleanup of temporary and old files
- Storage usage monitoring and reporting
- File archival and retention policies
- Cache management and optimization
- Storage health monitoring and alerts
"""

import os
import sys
import json
import gzip
import shutil
import hashlib
import zipfile
import tempfile
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set, Generator
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict, namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger

logger = get_logger(__name__)

try:
    import lzma
    HAS_LZMA = True
except ImportError:
    HAS_LZMA = False
    logger.warning("lzma not available - XZ compression disabled")


class CompressionType(Enum):
    """Available compression algorithms"""
    NONE = "none"
    GZIP = "gzip"
    ZIP = "zip"
    LZMA = "lzma"
    AUTO = "auto"


class FileCategory(Enum):
    """File categories for management"""
    LOG = "log"
    CACHE = "cache"
    TEMP = "temp"
    BACKUP = "backup"
    ARCHIVE = "archive"
    CONFIG = "config"
    DATA = "data"
    OTHER = "other"


class CleanupAction(Enum):
    """Cleanup actions that can be performed"""
    DELETE = "delete"
    COMPRESS = "compress"
    ARCHIVE = "archive"
    MOVE = "move"
    SKIP = "skip"


@dataclass
class StorageQuota:
    """Storage quota configuration"""
    max_total_size: int  # bytes
    max_file_age_days: int
    max_temp_size: int
    max_cache_size: int
    max_log_size: int
    compression_threshold: int = 10 * 1024 * 1024  # 10MB
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'max_total_size': self.max_total_size,
            'max_total_size_mb': round(self.max_total_size / (1024 * 1024), 2),
            'max_file_age_days': self.max_file_age_days,
            'max_temp_size': self.max_temp_size,
            'max_temp_size_mb': round(self.max_temp_size / (1024 * 1024), 2),
            'max_cache_size': self.max_cache_size,
            'max_cache_size_mb': round(self.max_cache_size / (1024 * 1024), 2),
            'max_log_size': self.max_log_size,
            'max_log_size_mb': round(self.max_log_size / (1024 * 1024), 2),
            'compression_threshold': self.compression_threshold,
            'compression_threshold_mb': round(self.compression_threshold / (1024 * 1024), 2)
        }


@dataclass
class FileInfo:
    """Information about a file"""
    path: Path
    size: int
    modified_time: datetime
    accessed_time: datetime
    category: FileCategory
    is_compressed: bool = False
    checksum: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'path': str(self.path),
            'size': self.size,
            'size_mb': round(self.size / (1024 * 1024), 4),
            'modified_time': self.modified_time.isoformat(),
            'accessed_time': self.accessed_time.isoformat(),
            'category': self.category.value,
            'is_compressed': self.is_compressed,
            'checksum': self.checksum
        }


@dataclass
class CleanupResult:
    """Result of a cleanup operation"""
    action: CleanupAction
    file_path: Path
    original_size: int
    final_size: int
    space_saved: int
    success: bool
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'action': self.action.value,
            'file_path': str(self.file_path),
            'original_size': self.original_size,
            'original_size_mb': round(self.original_size / (1024 * 1024), 4),
            'final_size': self.final_size,
            'final_size_mb': round(self.final_size / (1024 * 1024), 4),
            'space_saved': self.space_saved,
            'space_saved_mb': round(self.space_saved / (1024 * 1024), 4),
            'success': self.success,
            'error': self.error
        }


@dataclass
class StorageReport:
    """Comprehensive storage usage report"""
    total_size: int
    total_files: int
    by_category: Dict[FileCategory, Dict[str, Any]]
    largest_files: List[FileInfo]
    oldest_files: List[FileInfo]
    compression_candidates: List[FileInfo]
    cleanup_recommendations: List[Dict[str, Any]]
    quota_status: Dict[str, Any]
    generated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_size': self.total_size,
            'total_size_mb': round(self.total_size / (1024 * 1024), 2),
            'total_files': self.total_files,
            'by_category': {
                cat.value: stats for cat, stats in self.by_category.items()
            },
            'largest_files': [f.to_dict() for f in self.largest_files],
            'oldest_files': [f.to_dict() for f in self.oldest_files],
            'compression_candidates': [f.to_dict() for f in self.compression_candidates],
            'cleanup_recommendations': self.cleanup_recommendations,
            'quota_status': self.quota_status,
            'generated_at': self.generated_at.isoformat()
        }


class CompressionManager:
    """Handles file compression and decompression operations"""
    
    def __init__(self):
        self.supported_formats = {
            CompressionType.GZIP: ['.gz'],
            CompressionType.ZIP: ['.zip'],
        }
        
        if HAS_LZMA:
            self.supported_formats[CompressionType.LZMA] = ['.xz', '.lzma']
    
    def compress_file(self, file_path: Path, compression_type: CompressionType = CompressionType.AUTO,
                     remove_original: bool = True) -> Tuple[Path, int]:
        """
        Compress a file using the specified compression algorithm.
        
        Args:
            file_path: Path to the file to compress
            compression_type: Compression algorithm to use
            remove_original: Whether to remove the original file
            
        Returns:
            Tuple of (compressed_file_path, space_saved)
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        original_size = file_path.stat().st_size
        
        # Auto-select compression type
        if compression_type == CompressionType.AUTO:
            compression_type = self._select_best_compression(file_path)
        
        if compression_type == CompressionType.NONE:
            return file_path, 0
        
        # Determine output path
        if compression_type == CompressionType.GZIP:
            output_path = file_path.with_suffix(file_path.suffix + '.gz')
            self._compress_gzip(file_path, output_path)
        elif compression_type == CompressionType.ZIP:
            output_path = file_path.with_suffix('.zip')
            self._compress_zip(file_path, output_path)
        elif compression_type == CompressionType.LZMA and HAS_LZMA:
            output_path = file_path.with_suffix(file_path.suffix + '.xz')
            self._compress_lzma(file_path, output_path)
        else:
            raise ValueError(f"Unsupported compression type: {compression_type}")
        
        compressed_size = output_path.stat().st_size
        space_saved = original_size - compressed_size
        
        if remove_original:
            file_path.unlink()
        
        logger.info(
            "Compressed %s: %d bytes -> %d bytes (%.1f%% reduction)",
            file_path.name,
            original_size,
            compressed_size,
            (space_saved / original_size) * 100 if original_size > 0 else 0
        )
        
        return output_path, space_saved
    
    def decompress_file(self, compressed_path: Path, remove_compressed: bool = True) -> Path:
        """
        Decompress a compressed file.
        
        Args:
            compressed_path: Path to the compressed file
            remove_compressed: Whether to remove the compressed file
            
        Returns:
            Path to the decompressed file
        """
        if not compressed_path.exists():
            raise FileNotFoundError(f"Compressed file not found: {compressed_path}")
        
        # Determine compression type from extension
        suffix = compressed_path.suffix.lower()
        
        if suffix == '.gz':
            output_path = Path(str(compressed_path)[:-3])  # Remove .gz
            self._decompress_gzip(compressed_path, output_path)
        elif suffix == '.zip':
            # For ZIP files, we need to extract the contents
            output_path = self._decompress_zip(compressed_path)
        elif suffix in ['.xz', '.lzma'] and HAS_LZMA:
            output_path = Path(str(compressed_path).rsplit('.', 1)[0])  # Remove last extension
            self._decompress_lzma(compressed_path, output_path)
        else:
            raise ValueError(f"Unsupported compressed file format: {suffix}")
        
        if remove_compressed:
            compressed_path.unlink()
        
        logger.info("Decompressed %s -> %s", compressed_path.name, output_path.name)
        return output_path
    
    def _select_best_compression(self, file_path: Path) -> CompressionType:
        """Select the best compression algorithm for a file"""
        # Check file size
        size = file_path.stat().st_size
        
        # Don't compress small files
        if size < 1024:  # 1KB
            return CompressionType.NONE
        
        # Don't compress already compressed files
        suffix = file_path.suffix.lower()
        compressed_extensions = {'.gz', '.zip', '.7z', '.rar', '.bz2', '.xz', '.lzma'}
        if suffix in compressed_extensions:
            return CompressionType.NONE
        
        # Don't compress binary formats that are already compressed
        binary_compressed = {'.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mp3', '.pdf', '.docx', '.xlsx'}
        if suffix in binary_compressed:
            return CompressionType.NONE
        
        # For text files and logs, use GZIP for best compatibility
        text_extensions = {'.txt', '.log', '.csv', '.json', '.xml', '.html', '.css', '.js', '.py', '.md'}
        if suffix in text_extensions:
            return CompressionType.GZIP
        
        # For larger files, use LZMA for better compression ratio
        if size > 100 * 1024 * 1024 and HAS_LZMA:  # 100MB
            return CompressionType.LZMA
        
        # Default to GZIP
        return CompressionType.GZIP
    
    def _compress_gzip(self, source: Path, target: Path):
        """Compress file using gzip"""
        with open(source, 'rb') as src, gzip.open(target, 'wb') as dst:
            shutil.copyfileobj(src, dst)
    
    def _compress_zip(self, source: Path, target: Path):
        """Compress file using zip"""
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(source, source.name)
    
    def _compress_lzma(self, source: Path, target: Path):
        """Compress file using LZMA"""
        with open(source, 'rb') as src, lzma.open(target, 'wb') as dst:
            shutil.copyfileobj(src, dst)
    
    def _decompress_gzip(self, source: Path, target: Path):
        """Decompress gzip file"""
        with gzip.open(source, 'rb') as src, open(target, 'wb') as dst:
            shutil.copyfileobj(src, dst)
    
    def _decompress_zip(self, source: Path) -> Path:
        """Decompress zip file and return the path to the extracted file"""
        extract_dir = source.parent / f"extracted_{source.stem}"
        extract_dir.mkdir(exist_ok=True)
        
        with zipfile.ZipFile(source, 'r') as zf:
            zf.extractall(extract_dir)
            
            # Return the path to the first extracted file
            extracted_files = list(extract_dir.iterdir())
            if extracted_files:
                return extracted_files[0]
        
        raise RuntimeError(f"No files extracted from {source}")
    
    def _decompress_lzma(self, source: Path, target: Path):
        """Decompress LZMA file"""
        with lzma.open(source, 'rb') as src, open(target, 'wb') as dst:
            shutil.copyfileobj(src, dst)


class StorageManager:
    """
    Main storage management system.
    
    Provides comprehensive storage management including cleanup,
    compression, monitoring, and optimization.
    """
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path).resolve()
        self.compression_manager = CompressionManager()
        self.quota = self._get_default_quota()
        self.exclude_patterns = {
            '.git', '__pycache__', '.pytest_cache', 'node_modules',
            '.vscode', '.idea', '*.pyc', '*.pyo', '*.pyd'
        }
        self.category_patterns = self._get_category_patterns()
        self.lock = threading.RLock()
        
        logger.info("Storage manager initialized for path: %s", self.base_path)
    
    def _get_default_quota(self) -> StorageQuota:
        """Get default storage quota settings"""
        return StorageQuota(
            max_total_size=5 * 1024 * 1024 * 1024,  # 5GB
            max_file_age_days=365,  # 1 year
            max_temp_size=1 * 1024 * 1024 * 1024,   # 1GB
            max_cache_size=2 * 1024 * 1024 * 1024,  # 2GB
            max_log_size=500 * 1024 * 1024,         # 500MB
            compression_threshold=10 * 1024 * 1024   # 10MB
        )
    
    def _get_category_patterns(self) -> Dict[FileCategory, List[str]]:
        """Get file patterns for categorization"""
        return {
            FileCategory.LOG: ['*.log', '*.log.*', 'logs/*', 'app.log*'],
            FileCategory.CACHE: ['*cache*', '*.cache', '__pycache__/*', '*.pyc', '.pytest_cache/*'],
            FileCategory.TEMP: ['tmp/*', 'temp/*', '*.tmp', '*.temp', '.tmp*'],
            FileCategory.BACKUP: ['*.bak', '*.backup', '*backup*', '*.old'],
            FileCategory.ARCHIVE: ['*.zip', '*.gz', '*.tar', '*.7z', '*.rar'],
            FileCategory.CONFIG: ['*.conf', '*.config', '*.ini', '*.yaml', '*.yml', '*.json'],
            FileCategory.DATA: ['*.db', '*.sqlite', '*.sqlite3', '*.csv', '*.json']
        }
    
    def scan_storage(self, include_checksums: bool = False) -> List[FileInfo]:
        """
        Scan storage directory and collect file information.
        
        Args:
            include_checksums: Whether to calculate file checksums
            
        Returns:
            List of FileInfo objects
        """
        files = []
        
        logger.info("Scanning storage directory: %s", self.base_path)
        
        for file_path in self._walk_files():
            try:
                stat = file_path.stat()
                
                file_info = FileInfo(
                    path=file_path,
                    size=stat.st_size,
                    modified_time=datetime.fromtimestamp(stat.st_mtime),
                    accessed_time=datetime.fromtimestamp(stat.st_atime),
                    category=self._categorize_file(file_path),
                    is_compressed=self._is_compressed(file_path)
                )
                
                if include_checksums:
                    file_info.checksum = self._calculate_checksum(file_path)
                
                files.append(file_info)
                
            except (OSError, PermissionError) as e:
                logger.warning("Could not access file %s: %s", file_path, e)
        
        logger.info("Scanned %d files", len(files))
        return files
    
    def _walk_files(self) -> Generator[Path, None, None]:
        """Walk through all files in the storage directory"""
        for root, dirs, files in os.walk(self.base_path):
            root_path = Path(root)
            
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not self._is_excluded(root_path / d)]
            
            for file in files:
                file_path = root_path / file
                if not self._is_excluded(file_path):
                    yield file_path
    
    def _is_excluded(self, path: Path) -> bool:
        """Check if a path should be excluded"""
        path_str = str(path.relative_to(self.base_path))
        
        for pattern in self.exclude_patterns:
            if pattern.startswith('*') and path.name.endswith(pattern[1:]):
                return True
            elif pattern.endswith('*') and path.name.startswith(pattern[:-1]):
                return True
            elif pattern in path_str:
                return True
        
        return False
    
    def _categorize_file(self, file_path: Path) -> FileCategory:
        """Categorize a file based on its path and name"""
        relative_path = file_path.relative_to(self.base_path)
        path_str = str(relative_path).lower()
        name_str = file_path.name.lower()
        
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if pattern.startswith('*') and pattern.endswith('*'):
                    if pattern[1:-1] in name_str:
                        return category
                elif pattern.startswith('*'):
                    if name_str.endswith(pattern[1:]):
                        return category
                elif pattern.endswith('*'):
                    if name_str.startswith(pattern[:-1]):
                        return category
                elif '/' in pattern:
                    if pattern.replace('*', '') in path_str:
                        return category
                elif pattern in name_str:
                    return category
        
        return FileCategory.OTHER
    
    def _is_compressed(self, file_path: Path) -> bool:
        """Check if a file is already compressed"""
        compressed_extensions = {'.gz', '.zip', '.7z', '.rar', '.bz2', '.xz', '.lzma'}
        return file_path.suffix.lower() in compressed_extensions
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file"""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.warning("Could not calculate checksum for %s: %s", file_path, e)
            return ""
    
    def generate_storage_report(self, include_checksums: bool = False) -> StorageReport:
        """
        Generate comprehensive storage usage report.
        
        Args:
            include_checksums: Whether to include file checksums
            
        Returns:
            StorageReport object
        """
        logger.info("Generating storage report...")
        
        files = self.scan_storage(include_checksums)
        
        # Calculate totals
        total_size = sum(f.size for f in files)
        total_files = len(files)
        
        # Group by category
        by_category = {}
        for category in FileCategory:
            category_files = [f for f in files if f.category == category]
            by_category[category] = {
                'count': len(category_files),
                'total_size': sum(f.size for f in category_files),
                'total_size_mb': round(sum(f.size for f in category_files) / (1024 * 1024), 2),
                'avg_size': sum(f.size for f in category_files) / len(category_files) if category_files else 0,
                'oldest_file': min(category_files, key=lambda x: x.modified_time) if category_files else None,
                'largest_file': max(category_files, key=lambda x: x.size) if category_files else None
            }
        
        # Find largest files
        largest_files = sorted(files, key=lambda x: x.size, reverse=True)[:20]
        
        # Find oldest files
        oldest_files = sorted(files, key=lambda x: x.modified_time)[:20]
        
        # Find compression candidates
        compression_candidates = [
            f for f in files
            if not f.is_compressed and f.size >= self.quota.compression_threshold
            and f.category in [FileCategory.LOG, FileCategory.DATA, FileCategory.OTHER]
        ]
        compression_candidates.sort(key=lambda x: x.size, reverse=True)
        
        # Generate cleanup recommendations
        cleanup_recommendations = self._generate_cleanup_recommendations(files)
        
        # Check quota status
        quota_status = {
            'total_size_limit': self.quota.max_total_size,
            'total_size_current': total_size,
            'total_size_usage_percent': (total_size / self.quota.max_total_size) * 100,
            'over_quota': total_size > self.quota.max_total_size,
            'temp_size_limit': self.quota.max_temp_size,
            'temp_size_current': by_category[FileCategory.TEMP]['total_size'],
            'cache_size_limit': self.quota.max_cache_size,
            'cache_size_current': by_category[FileCategory.CACHE]['total_size'],
            'log_size_limit': self.quota.max_log_size,
            'log_size_current': by_category[FileCategory.LOG]['total_size']
        }
        
        report = StorageReport(
            total_size=total_size,
            total_files=total_files,
            by_category=by_category,
            largest_files=largest_files,
            oldest_files=oldest_files,
            compression_candidates=compression_candidates,
            cleanup_recommendations=cleanup_recommendations,
            quota_status=quota_status
        )
        
        logger.info("Storage report generated: %d files, %.2f MB total", 
                   total_files, total_size / (1024 * 1024))
        
        return report
    
    def _generate_cleanup_recommendations(self, files: List[FileInfo]) -> List[Dict[str, Any]]:
        """Generate cleanup recommendations based on file analysis"""
        recommendations = []
        cutoff_date = datetime.now() - timedelta(days=self.quota.max_file_age_days)
        
        # Old files recommendation
        old_files = [f for f in files if f.modified_time < cutoff_date]
        if old_files:
            old_size = sum(f.size for f in old_files)
            recommendations.append({
                'type': 'delete_old_files',
                'description': f'Delete {len(old_files)} files older than {self.quota.max_file_age_days} days',
                'files_count': len(old_files),
                'space_savings': old_size,
                'space_savings_mb': round(old_size / (1024 * 1024), 2),
                'priority': 'high' if old_size > 100 * 1024 * 1024 else 'medium'
            })
        
        # Large file compression recommendation
        compression_candidates = [
            f for f in files
            if not f.is_compressed and f.size >= self.quota.compression_threshold
        ]
        if compression_candidates:
            # Estimate 30% compression ratio
            estimated_savings = sum(f.size for f in compression_candidates) * 0.3
            recommendations.append({
                'type': 'compress_large_files',
                'description': f'Compress {len(compression_candidates)} large files',
                'files_count': len(compression_candidates),
                'space_savings': estimated_savings,
                'space_savings_mb': round(estimated_savings / (1024 * 1024), 2),
                'priority': 'medium'
            })
        
        # Temporary files cleanup
        temp_files = [f for f in files if f.category == FileCategory.TEMP]
        if temp_files:
            temp_size = sum(f.size for f in temp_files)
            recommendations.append({
                'type': 'clean_temp_files',
                'description': f'Clean up {len(temp_files)} temporary files',
                'files_count': len(temp_files),
                'space_savings': temp_size,
                'space_savings_mb': round(temp_size / (1024 * 1024), 2),
                'priority': 'high'
            })
        
        # Cache cleanup for old cached files
        old_cache_cutoff = datetime.now() - timedelta(days=30)
        old_cache_files = [
            f for f in files 
            if f.category == FileCategory.CACHE and f.modified_time < old_cache_cutoff
        ]
        if old_cache_files:
            cache_size = sum(f.size for f in old_cache_files)
            recommendations.append({
                'type': 'clean_old_cache',
                'description': f'Clean up {len(old_cache_files)} old cache files',
                'files_count': len(old_cache_files),
                'space_savings': cache_size,
                'space_savings_mb': round(cache_size / (1024 * 1024), 2),
                'priority': 'medium'
            })
        
        return recommendations
    
    def perform_cleanup(self, max_workers: int = 4, dry_run: bool = False) -> List[CleanupResult]:
        """
        Perform automated storage cleanup.
        
        Args:
            max_workers: Maximum number of worker threads
            dry_run: If True, only simulate cleanup without making changes
            
        Returns:
            List of cleanup results
        """
        logger.info("Starting storage cleanup (dry_run=%s)", dry_run)
        
        files = self.scan_storage()
        cleanup_plan = self._create_cleanup_plan(files)
        results = []
        
        if not cleanup_plan:
            logger.info("No cleanup actions needed")
            return results
        
        logger.info("Cleanup plan created: %d actions", len(cleanup_plan))
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit cleanup tasks
            future_to_action = {}
            for action, file_path in cleanup_plan:
                future = executor.submit(self._execute_cleanup_action, action, file_path, dry_run)
                future_to_action[future] = (action, file_path)
            
            # Collect results
            for future in as_completed(future_to_action):
                action, file_path = future_to_action[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    result = CleanupResult(
                        action=action,
                        file_path=file_path,
                        original_size=0,
                        final_size=0,
                        space_saved=0,
                        success=False,
                        error=str(e)
                    )
                    results.append(result)
                    logger.error("Cleanup action failed for %s: %s", file_path, e)
        
        # Log summary
        successful_results = [r for r in results if r.success]
        total_space_saved = sum(r.space_saved for r in successful_results)
        
        logger.info(
            "Cleanup completed: %d/%d actions successful, %.2f MB saved",
            len(successful_results),
            len(results),
            total_space_saved / (1024 * 1024)
        )
        
        return results
    
    def _create_cleanup_plan(self, files: List[FileInfo]) -> List[Tuple[CleanupAction, Path]]:
        """Create a cleanup plan based on file analysis"""
        plan = []
        cutoff_date = datetime.now() - timedelta(days=self.quota.max_file_age_days)
        
        for file_info in files:
            action = self._determine_cleanup_action(file_info, cutoff_date)
            if action != CleanupAction.SKIP:
                plan.append((action, file_info.path))
        
        return plan
    
    def _determine_cleanup_action(self, file_info: FileInfo, cutoff_date: datetime) -> CleanupAction:
        """Determine what cleanup action should be taken for a file"""
        
        # Always delete temporary files
        if file_info.category == FileCategory.TEMP:
            return CleanupAction.DELETE
        
        # Delete very old files
        if file_info.modified_time < cutoff_date:
            return CleanupAction.DELETE
        
        # Compress large uncompressed files
        if (not file_info.is_compressed and 
            file_info.size >= self.quota.compression_threshold and
            file_info.category in [FileCategory.LOG, FileCategory.DATA, FileCategory.OTHER]):
            return CleanupAction.COMPRESS
        
        # Delete old cache files (older than 30 days)
        if (file_info.category == FileCategory.CACHE and
            file_info.modified_time < datetime.now() - timedelta(days=30)):
            return CleanupAction.DELETE
        
        return CleanupAction.SKIP
    
    def _execute_cleanup_action(self, action: CleanupAction, file_path: Path, dry_run: bool) -> CleanupResult:
        """Execute a single cleanup action"""
        if not file_path.exists():
            return CleanupResult(
                action=action,
                file_path=file_path,
                original_size=0,
                final_size=0,
                space_saved=0,
                success=False,
                error="File not found"
            )
        
        original_size = file_path.stat().st_size
        
        try:
            if dry_run:
                # Simulate the action
                if action == CleanupAction.DELETE:
                    final_size = 0
                    space_saved = original_size
                elif action == CleanupAction.COMPRESS:
                    # Estimate 30% compression ratio
                    final_size = int(original_size * 0.7)
                    space_saved = original_size - final_size
                else:
                    final_size = original_size
                    space_saved = 0
                
                return CleanupResult(
                    action=action,
                    file_path=file_path,
                    original_size=original_size,
                    final_size=final_size,
                    space_saved=space_saved,
                    success=True
                )
            
            # Execute the actual action
            if action == CleanupAction.DELETE:
                file_path.unlink()
                return CleanupResult(
                    action=action,
                    file_path=file_path,
                    original_size=original_size,
                    final_size=0,
                    space_saved=original_size,
                    success=True
                )
            
            elif action == CleanupAction.COMPRESS:
                compressed_path, space_saved = self.compression_manager.compress_file(
                    file_path, remove_original=True
                )
                final_size = compressed_path.stat().st_size
                
                return CleanupResult(
                    action=action,
                    file_path=file_path,
                    original_size=original_size,
                    final_size=final_size,
                    space_saved=space_saved,
                    success=True
                )
            
            else:
                return CleanupResult(
                    action=action,
                    file_path=file_path,
                    original_size=original_size,
                    final_size=original_size,
                    space_saved=0,
                    success=True
                )
                
        except Exception as e:
            return CleanupResult(
                action=action,
                file_path=file_path,
                original_size=original_size,
                final_size=original_size,
                space_saved=0,
                success=False,
                error=str(e)
            )
    
    def compress_files(self, file_patterns: List[str], compression_type: CompressionType = CompressionType.AUTO) -> List[Tuple[Path, int]]:
        """
        Compress files matching the given patterns.
        
        Args:
            file_patterns: List of file patterns to match
            compression_type: Compression algorithm to use
            
        Returns:
            List of (compressed_path, space_saved) tuples
        """
        results = []
        
        for pattern in file_patterns:
            matching_files = list(self.base_path.glob(pattern))
            
            for file_path in matching_files:
                if file_path.is_file() and not self._is_compressed(file_path):
                    try:
                        compressed_path, space_saved = self.compression_manager.compress_file(
                            file_path, compression_type
                        )
                        results.append((compressed_path, space_saved))
                        logger.info("Compressed %s, saved %d bytes", file_path.name, space_saved)
                    except Exception as e:
                        logger.error("Failed to compress %s: %s", file_path, e)
        
        return results
    
    def get_storage_health(self) -> Dict[str, Any]:
        """
        Get storage health status and recommendations.
        
        Returns:
            Dictionary with health status information
        """
        try:
            # Get current storage stats
            total, used, free = shutil.disk_usage(self.base_path)
            
            # Get file statistics
            files = self.scan_storage()
            total_managed_size = sum(f.size for f in files)
            
            # Calculate health metrics
            disk_usage_percent = (used / total) * 100
            fragmentation_estimate = len([f for f in files if f.size < 1024]) / len(files) * 100 if files else 0
            
            # Categorize files
            by_category = defaultdict(lambda: {'count': 0, 'size': 0})
            old_files_count = 0
            compressible_size = 0
            
            cutoff_date = datetime.now() - timedelta(days=self.quota.max_file_age_days)
            
            for file_info in files:
                by_category[file_info.category]['count'] += 1
                by_category[file_info.category]['size'] += file_info.size
                
                if file_info.modified_time < cutoff_date:
                    old_files_count += 1
                
                if not file_info.is_compressed and file_info.size >= self.quota.compression_threshold:
                    compressible_size += file_info.size
            
            health_score = 100
            warnings = []
            recommendations = []
            
            # Check disk usage
            if disk_usage_percent > 90:
                health_score -= 30
                warnings.append("Disk usage is critically high (>90%)")
                recommendations.append("Free up disk space immediately")
            elif disk_usage_percent > 80:
                health_score -= 15
                warnings.append("Disk usage is high (>80%)")
                recommendations.append("Consider cleaning up old files")
            
            # Check quota violations
            if total_managed_size > self.quota.max_total_size:
                health_score -= 20
                warnings.append("Storage quota exceeded")
                recommendations.append("Perform cleanup or increase quota")
            
            # Check for old files
            if old_files_count > 100:
                health_score -= 10
                warnings.append(f"{old_files_count} files are older than {self.quota.max_file_age_days} days")
                recommendations.append("Clean up old files")
            
            # Check compression opportunities
            if compressible_size > 100 * 1024 * 1024:  # 100MB
                health_score -= 5
                recommendations.append(f"Compress large files to save ~{int(compressible_size * 0.3 / 1024 / 1024)}MB")
            
            # Check fragmentation
            if fragmentation_estimate > 50:
                health_score -= 5
                warnings.append("High file fragmentation detected")
                recommendations.append("Consider consolidating small files")
            
            return {
                'health_score': max(0, health_score),
                'health_status': 'excellent' if health_score >= 90 else 
                               'good' if health_score >= 70 else
                               'fair' if health_score >= 50 else 'poor',
                'disk_usage': {
                    'total_bytes': total,
                    'used_bytes': used,
                    'free_bytes': free,
                    'usage_percent': disk_usage_percent
                },
                'managed_storage': {
                    'total_files': len(files),
                    'total_size': total_managed_size,
                    'by_category': {cat.value: stats for cat, stats in by_category.items()}
                },
                'metrics': {
                    'old_files_count': old_files_count,
                    'compressible_size': compressible_size,
                    'fragmentation_estimate': fragmentation_estimate
                },
                'warnings': warnings,
                'recommendations': recommendations,
                'quota_status': {
                    'current': total_managed_size,
                    'limit': self.quota.max_total_size,
                    'usage_percent': (total_managed_size / self.quota.max_total_size) * 100
                }
            }
            
        except Exception as e:
            logger.error("Error getting storage health: %s", e)
            return {
                'health_score': 0,
                'health_status': 'unknown',
                'error': str(e)
            }
    
    def set_quota(self, quota: StorageQuota):
        """Set storage quota configuration"""
        with self.lock:
            self.quota = quota
        logger.info("Storage quota updated: %s", quota.to_dict())
    
    def add_exclude_pattern(self, pattern: str):
        """Add a pattern to exclude from storage management"""
        with self.lock:
            self.exclude_patterns.add(pattern)
        logger.info("Added exclude pattern: %s", pattern)
    
    def remove_exclude_pattern(self, pattern: str):
        """Remove a pattern from exclusion list"""
        with self.lock:
            self.exclude_patterns.discard(pattern)
        logger.info("Removed exclude pattern: %s", pattern)


# Global storage manager instance
_storage_manager = None

def get_storage_manager(base_path: str = ".") -> StorageManager:
    """Get or create the global storage manager instance"""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager(base_path)
    return _storage_manager


def main():
    """Command line interface for storage management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 Storage Management")
    parser.add_argument('--path', default='.', help='Base path for storage management')
    parser.add_argument('--scan', action='store_true', help='Scan and report storage usage')
    parser.add_argument('--cleanup', action='store_true', help='Perform automated cleanup')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no changes)')
    parser.add_argument('--compress', nargs='+', help='Compress files matching patterns')
    parser.add_argument('--health', action='store_true', help='Show storage health status')
    parser.add_argument('--checksums', action='store_true', help='Include checksums in scan')
    
    args = parser.parse_args()
    
    manager = get_storage_manager(args.path)
    
    if args.scan:
        print("Scanning storage...")
        report = manager.generate_storage_report(include_checksums=args.checksums)
        print(json.dumps(report.to_dict(), indent=2))
    
    elif args.cleanup:
        print(f"Performing cleanup (dry_run={args.dry_run})...")
        results = manager.perform_cleanup(dry_run=args.dry_run)
        
        print(f"\nCleanup Results:")
        print(f"Actions performed: {len(results)}")
        successful = [r for r in results if r.success]
        print(f"Successful: {len(successful)}")
        total_saved = sum(r.space_saved for r in successful)
        print(f"Total space saved: {total_saved / (1024 * 1024):.2f} MB")
        
        for result in results:
            print(f"  {result.action.value}: {result.file_path.name} "
                  f"({'OK' if result.success else 'FAILED'})")
            if not result.success and result.error:
                print(f"    Error: {result.error}")
    
    elif args.compress:
        print(f"Compressing files: {args.compress}")
        results = manager.compress_files(args.compress)
        
        total_saved = sum(space_saved for _, space_saved in results)
        print(f"Compressed {len(results)} files, saved {total_saved / (1024 * 1024):.2f} MB")
    
    elif args.health:
        print("Checking storage health...")
        health = manager.get_storage_health()
        print(json.dumps(health, indent=2))
    
    else:
        print("JARVIS-MK42 Storage Management System")
        print("Use --help for available options")


if __name__ == "__main__":
    main()
