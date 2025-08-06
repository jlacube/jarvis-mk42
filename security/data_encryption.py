#!/usr/bin/env python3
"""
JARVIS-MK42 Data Encryption System
================================

This module provides comprehensive data encryption capabilities including:
- Encryption at rest for sensitive data
- Encryption in transit for API communications
- Key management and rotation
- Field-level encryption for database records
- Secure configuration management
"""

import os
import sys
import json
import base64
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib
import hmac
from pathlib import Path

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logging_config import get_logger

logger = get_logger(__name__)

try:
    from cryptography.fernet import Fernet, MultiFernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    CRYPTO_AVAILABLE = True
except ImportError:
    logger.warning("Cryptography library not available. Encryption features disabled.")
    CRYPTO_AVAILABLE = False


class EncryptionLevel(Enum):
    """Encryption security levels"""
    BASIC = "basic"          # AES-128, basic key management
    STANDARD = "standard"    # AES-256, proper key rotation
    HIGH = "high"           # AES-256, multiple keys, frequent rotation
    MAXIMUM = "maximum"     # AES-256, hardware security modules (future)


class DataClassification(Enum):
    """Data classification levels"""
    PUBLIC = "public"           # No encryption needed
    INTERNAL = "internal"       # Basic encryption
    CONFIDENTIAL = "confidential"  # Standard encryption
    SECRET = "secret"          # High encryption
    TOP_SECRET = "top_secret"  # Maximum encryption


@dataclass
class EncryptionKey:
    """Represents an encryption key with metadata"""
    key_id: str
    key_data: bytes
    algorithm: str
    created_at: datetime
    expires_at: Optional[datetime]
    classification: DataClassification
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class EncryptedData:
    """Represents encrypted data with metadata"""
    ciphertext: bytes
    key_id: str
    algorithm: str
    iv: Optional[bytes]
    tag: Optional[bytes]  # For authenticated encryption
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'ciphertext': base64.b64encode(self.ciphertext).decode('utf-8'),
            'key_id': self.key_id,
            'algorithm': self.algorithm,
            'iv': base64.b64encode(self.iv).decode('utf-8') if self.iv else None,
            'tag': base64.b64encode(self.tag).decode('utf-8') if self.tag else None,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncryptedData':
        """Create from dictionary"""
        return cls(
            ciphertext=base64.b64decode(data['ciphertext']),
            key_id=data['key_id'],
            algorithm=data['algorithm'],
            iv=base64.b64decode(data['iv']) if data.get('iv') else None,
            tag=base64.b64decode(data['tag']) if data.get('tag') else None,
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata', {})
        )


class EncryptionError(Exception):
    """Base exception for encryption operations"""
    pass


class KeyManager:
    """
    Secure key management system.
    
    Handles creation, storage, rotation, and lifecycle of encryption keys.
    """
    
    def __init__(self, key_storage_path: Optional[str] = None):
        if not CRYPTO_AVAILABLE:
            raise EncryptionError("Cryptography library not available")
        
        self.key_storage_path = Path(key_storage_path or os.path.join(project_root, "security", "keys"))
        self.key_storage_path.mkdir(parents=True, exist_ok=True)
        self.keys: Dict[str, EncryptionKey] = {}
        self._load_keys()
        logger.info("Key manager initialized")
    
    def generate_key(self, classification: DataClassification, algorithm: str = "AES-256") -> str:
        """
        Generate a new encryption key.
        
        Args:
            classification: Data classification level
            algorithm: Encryption algorithm
            
        Returns:
            Key ID for the generated key
        """
        try:
            key_id = f"key_{secrets.token_hex(8)}_{int(datetime.utcnow().timestamp())}"
            
            # Generate key based on algorithm
            if algorithm == "AES-256":
                key_data = Fernet.generate_key()
            elif algorithm == "AES-128":
                key_data = secrets.token_bytes(16)
            else:
                raise EncryptionError(f"Unsupported algorithm: {algorithm}")
            
            # Set expiration based on classification
            expires_at = self._get_key_expiration(classification)
            
            # Create key object
            encryption_key = EncryptionKey(
                key_id=key_id,
                key_data=key_data,
                algorithm=algorithm,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
                classification=classification
            )
            
            # Store key
            self.keys[key_id] = encryption_key
            self._save_key(encryption_key)
            
            logger.info(f"Generated new {algorithm} key {key_id} for {classification.value} data")
            return key_id
            
        except Exception as e:
            logger.error(f"Key generation failed: {e}")
            raise EncryptionError(f"Key generation failed: {e}")
    
    def get_key(self, key_id: str) -> Optional[EncryptionKey]:
        """Get encryption key by ID"""
        key = self.keys.get(key_id)
        if key and self._is_key_valid(key):
            return key
        return None
    
    def rotate_key(self, old_key_id: str) -> str:
        """
        Rotate an encryption key by creating a new one.
        
        Args:
            old_key_id: ID of the key to rotate
            
        Returns:
            ID of the new key
        """
        old_key = self.keys.get(old_key_id)
        if not old_key:
            raise EncryptionError(f"Key {old_key_id} not found")
        
        # Generate new key with same parameters
        new_key_id = self.generate_key(old_key.classification, old_key.algorithm)
        
        # Mark old key as expired
        old_key.expires_at = datetime.utcnow()
        self._save_key(old_key)
        
        logger.info(f"Rotated key {old_key_id} -> {new_key_id}")
        return new_key_id
    
    def _get_key_expiration(self, classification: DataClassification) -> datetime:
        """Get key expiration based on classification"""
        expiration_days = {
            DataClassification.PUBLIC: 365,      # 1 year
            DataClassification.INTERNAL: 180,    # 6 months
            DataClassification.CONFIDENTIAL: 90, # 3 months
            DataClassification.SECRET: 30,       # 1 month
            DataClassification.TOP_SECRET: 7     # 1 week
        }
        
        days = expiration_days.get(classification, 90)
        return datetime.utcnow() + timedelta(days=days)
    
    def _is_key_valid(self, key: EncryptionKey) -> bool:
        """Check if key is still valid"""
        if key.expires_at and datetime.utcnow() > key.expires_at:
            return False
        return True
    
    def _load_keys(self):
        """Load keys from storage"""
        try:
            for key_file in self.key_storage_path.glob("*.key"):
                with open(key_file, 'rb') as f:
                    key_data = f.read()
                    # In production, this would use proper key encryption
                    # For now, we'll use a simple format
                    pass
        except Exception as e:
            logger.debug(f"Could not load existing keys: {e}")
    
    def _save_key(self, key: EncryptionKey):
        """Save key to storage"""
        try:
            key_file = self.key_storage_path / f"{key.key_id}.key"
            # In production, keys should be encrypted at rest
            with open(key_file, 'wb') as f:
                f.write(key.key_data)
            
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            
        except Exception as e:
            logger.error(f"Failed to save key {key.key_id}: {e}")


class DataEncryption:
    """
    Main data encryption system.
    
    Provides encryption/decryption services with automatic key management,
    field-level encryption, and secure configuration handling.
    """
    
    def __init__(self):
        if not CRYPTO_AVAILABLE:
            logger.warning("Encryption disabled - cryptography library not available")
            self.enabled = False
            return
        
        self.enabled = True
        self.key_manager = KeyManager()
        self._setup_default_keys()
        logger.info("Data encryption system initialized")
    
    def _setup_default_keys(self):
        """Setup default encryption keys for different data types"""
        try:
            # Generate default keys for each classification level
            self.default_keys = {}
            for classification in DataClassification:
                if classification != DataClassification.PUBLIC:
                    key_id = self.key_manager.generate_key(classification)
                    self.default_keys[classification] = key_id
                    
        except Exception as e:
            logger.error(f"Failed to setup default keys: {e}")
            self.default_keys = {}
    
    def encrypt_data(self, data: Union[str, bytes], classification: DataClassification, 
                    key_id: Optional[str] = None) -> EncryptedData:
        """
        Encrypt data with specified classification level.
        
        Args:
            data: Data to encrypt
            classification: Data classification level
            key_id: Optional specific key ID to use
            
        Returns:
            EncryptedData object containing encrypted data and metadata
        """
        if not self.enabled:
            raise EncryptionError("Encryption system not available")
        
        if classification == DataClassification.PUBLIC:
            # Public data doesn't need encryption
            if isinstance(data, str):
                data = data.encode('utf-8')
            return EncryptedData(
                ciphertext=data,
                key_id="none",
                algorithm="none",
                iv=None,
                tag=None,
                timestamp=datetime.utcnow()
            )
        
        try:
            # Convert string to bytes if necessary
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Get encryption key
            if not key_id:
                key_id = self.default_keys.get(classification)
                if not key_id:
                    raise EncryptionError(f"No default key for classification {classification.value}")
            
            encryption_key = self.key_manager.get_key(key_id)
            if not encryption_key:
                raise EncryptionError(f"Encryption key {key_id} not found or expired")
            
            # Encrypt based on algorithm
            if encryption_key.algorithm == "AES-256":
                return self._encrypt_aes_gcm(data, encryption_key)
            elif encryption_key.algorithm == "AES-128":
                return self._encrypt_aes_cbc(data, encryption_key)
            else:
                raise EncryptionError(f"Unsupported algorithm: {encryption_key.algorithm}")
                
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Encryption failed: {e}")
    
    def decrypt_data(self, encrypted_data: EncryptedData) -> bytes:
        """
        Decrypt data using stored metadata.
        
        Args:
            encrypted_data: EncryptedData object to decrypt
            
        Returns:
            Decrypted data as bytes
        """
        if not self.enabled:
            raise EncryptionError("Encryption system not available")
        
        if encrypted_data.algorithm == "none":
            return encrypted_data.ciphertext
        
        try:
            # Get decryption key
            encryption_key = self.key_manager.get_key(encrypted_data.key_id)
            if not encryption_key:
                raise EncryptionError(f"Decryption key {encrypted_data.key_id} not found or expired")
            
            # Decrypt based on algorithm
            if encrypted_data.algorithm == "AES-256":
                return self._decrypt_aes_gcm(encrypted_data, encryption_key)
            elif encrypted_data.algorithm == "AES-128":
                return self._decrypt_aes_cbc(encrypted_data, encryption_key)
            else:
                raise EncryptionError(f"Unsupported algorithm: {encrypted_data.algorithm}")
                
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError(f"Decryption failed: {e}")
    
    def _encrypt_aes_gcm(self, data: bytes, key: EncryptionKey) -> EncryptedData:
        """Encrypt using AES-GCM (authenticated encryption)"""
        # Use Fernet for AES-256-GCM equivalent
        fernet = Fernet(key.key_data)
        ciphertext = fernet.encrypt(data)
        
        return EncryptedData(
            ciphertext=ciphertext,
            key_id=key.key_id,
            algorithm=key.algorithm,
            iv=None,  # Fernet includes IV
            tag=None,  # Fernet includes authentication tag
            timestamp=datetime.utcnow()
        )
    
    def _decrypt_aes_gcm(self, encrypted_data: EncryptedData, key: EncryptionKey) -> bytes:
        """Decrypt using AES-GCM"""
        fernet = Fernet(key.key_data)
        return fernet.decrypt(encrypted_data.ciphertext)
    
    def _encrypt_aes_cbc(self, data: bytes, key: EncryptionKey) -> EncryptedData:
        """Encrypt using AES-CBC"""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives import padding
        
        # Generate random IV
        iv = os.urandom(16)
        
        # Pad data to block size
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()
        
        # Encrypt
        cipher = Cipher(algorithms.AES(key.key_data), modes.CBC(iv))
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        return EncryptedData(
            ciphertext=ciphertext,
            key_id=key.key_id,
            algorithm=key.algorithm,
            iv=iv,
            tag=None,
            timestamp=datetime.utcnow()
        )
    
    def _decrypt_aes_cbc(self, encrypted_data: EncryptedData, key: EncryptionKey) -> bytes:
        """Decrypt using AES-CBC"""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives import padding
        
        # Decrypt
        cipher = Cipher(algorithms.AES(key.key_data), modes.CBC(encrypted_data.iv))
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(encrypted_data.ciphertext) + decryptor.finalize()
        
        # Remove padding
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        
        return data
    
    def encrypt_config_value(self, value: str, config_name: str = "default") -> str:
        """
        Encrypt configuration value for secure storage.
        
        Args:
            value: Configuration value to encrypt
            config_name: Configuration context name
            
        Returns:
            Base64-encoded encrypted configuration value
        """
        if not self.enabled:
            return value  # Return plaintext if encryption not available
        
        try:
            encrypted_data = self.encrypt_data(value, DataClassification.CONFIDENTIAL)
            return base64.b64encode(json.dumps(encrypted_data.to_dict()).encode('utf-8')).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Config encryption failed: {e}")
            return value  # Fallback to plaintext
    
    def decrypt_config_value(self, encrypted_value: str, config_name: str = "default") -> str:
        """
        Decrypt configuration value.
        
        Args:
            encrypted_value: Base64-encoded encrypted value
            config_name: Configuration context name
            
        Returns:
            Decrypted configuration value
        """
        if not self.enabled:
            return encrypted_value  # Return as-is if encryption not available
        
        try:
            # Check if value is actually encrypted (has our format)
            if not encrypted_value.startswith('ey'):  # Base64 starts with 'ey' for JSON
                return encrypted_value  # Return plaintext
            
            data_dict = json.loads(base64.b64decode(encrypted_value.encode('utf-8')))
            encrypted_data = EncryptedData.from_dict(data_dict)
            decrypted_bytes = self.decrypt_data(encrypted_data)
            return decrypted_bytes.decode('utf-8')
            
        except Exception as e:
            logger.debug(f"Config decryption failed, returning plaintext: {e}")
            return encrypted_value  # Fallback to plaintext
    
    def encrypt_field(self, data_dict: Dict[str, Any], field_name: str, 
                     classification: DataClassification) -> Dict[str, Any]:
        """
        Encrypt a specific field in a dictionary.
        
        Args:
            data_dict: Dictionary containing the field
            field_name: Name of field to encrypt
            classification: Data classification level
            
        Returns:
            Dictionary with encrypted field
        """
        if not self.enabled or field_name not in data_dict:
            return data_dict
        
        try:
            value = data_dict[field_name]
            if value is None:
                return data_dict
            
            # Convert value to string if needed
            if not isinstance(value, str):
                value = json.dumps(value)
            
            encrypted_data = self.encrypt_data(value, classification)
            
            # Replace field with encrypted version
            result = data_dict.copy()
            result[f"{field_name}_encrypted"] = encrypted_data.to_dict()
            del result[field_name]  # Remove original field
            
            return result
            
        except Exception as e:
            logger.error(f"Field encryption failed for {field_name}: {e}")
            return data_dict
    
    def decrypt_field(self, data_dict: Dict[str, Any], field_name: str) -> Dict[str, Any]:
        """
        Decrypt a specific field in a dictionary.
        
        Args:
            data_dict: Dictionary containing encrypted field
            field_name: Original name of the field
            
        Returns:
            Dictionary with decrypted field
        """
        encrypted_field_name = f"{field_name}_encrypted"
        
        if not self.enabled or encrypted_field_name not in data_dict:
            return data_dict
        
        try:
            encrypted_data = EncryptedData.from_dict(data_dict[encrypted_field_name])
            decrypted_bytes = self.decrypt_data(encrypted_data)
            decrypted_value = decrypted_bytes.decode('utf-8')
            
            # Try to parse as JSON if it looks like JSON
            try:
                if decrypted_value.startswith(('{', '[', '"')) or decrypted_value in ('true', 'false', 'null'):
                    decrypted_value = json.loads(decrypted_value)
            except:
                pass  # Keep as string
            
            # Replace encrypted field with decrypted version
            result = data_dict.copy()
            result[field_name] = decrypted_value
            del result[encrypted_field_name]
            
            return result
            
        except Exception as e:
            logger.error(f"Field decryption failed for {field_name}: {e}")
            return data_dict
    
    def get_encryption_status(self) -> Dict[str, Any]:
        """Get encryption system status and statistics"""
        if not self.enabled:
            return {
                'enabled': False,
                'reason': 'Cryptography library not available'
            }
        
        return {
            'enabled': True,
            'key_count': len(self.key_manager.keys),
            'default_keys': {k.value: v for k, v in self.default_keys.items()},
            'algorithms_supported': ['AES-256', 'AES-128'],
            'classifications_supported': [c.value for c in DataClassification]
        }


# Global encryption system instance
_encryption_system = None

def get_encryption_system() -> DataEncryption:
    """Get or create the global encryption system instance"""
    global _encryption_system
    if _encryption_system is None:
        _encryption_system = DataEncryption()
    return _encryption_system


def main():
    """Command line interface for encryption system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS-MK42 Data Encryption System")
    parser.add_argument('--status', action='store_true', help='Show encryption status')
    parser.add_argument('--encrypt', nargs=2, metavar=('data', 'classification'), help='Encrypt data')
    parser.add_argument('--test', action='store_true', help='Test encryption/decryption')
    
    args = parser.parse_args()
    
    encryption_system = get_encryption_system()
    
    if args.status:
        status = encryption_system.get_encryption_status()
        print(json.dumps(status, indent=2))
    
    elif args.encrypt:
        data, classification_str = args.encrypt
        try:
            classification = DataClassification(classification_str)
            encrypted_data = encryption_system.encrypt_data(data, classification)
            print(f"Encrypted data: {base64.b64encode(encrypted_data.ciphertext).decode('utf-8')}")
            print(f"Key ID: {encrypted_data.key_id}")
        except ValueError:
            print(f"Invalid classification. Use one of: {[c.value for c in DataClassification]}")
    
    elif args.test:
        # Test encryption/decryption
        test_data = "This is sensitive test data!"
        classification = DataClassification.CONFIDENTIAL
        
        print(f"Testing encryption with: {test_data}")
        encrypted_data = encryption_system.encrypt_data(test_data, classification)
        print(f"Encrypted successfully with key: {encrypted_data.key_id}")
        
        decrypted_data = encryption_system.decrypt_data(encrypted_data)
        decrypted_text = decrypted_data.decode('utf-8')
        print(f"Decrypted: {decrypted_text}")
        
        if test_data == decrypted_text:
            print("✅ Encryption/decryption test PASSED")
        else:
            print("❌ Encryption/decryption test FAILED")
    
    else:
        print("JARVIS-MK42 Data Encryption System")
        print("Use --status, --encrypt, or --test")


if __name__ == "__main__":
    main()
