# models/database.py
"""
Database models for Jarvis-MK42
"""

from sqlalchemy import Column, String, DateTime, Text, JSON, Boolean, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

Base = declarative_base()

class User(Base):
    """User model for authentication and user management"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Security
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    
    # User preferences
    preferred_language = Column(String(10), default="en", nullable=False)
    preferences = Column(JSON, default=dict, nullable=False)
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

class Session(Base):
    """Session model for managing user sessions"""
    __tablename__ = "sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    
    # Session data
    session_data = Column(JSON, default=dict, nullable=False)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Session state
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    conversations = relationship("Conversation", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id})>"
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at.replace(tzinfo=None)

class Conversation(Base):
    """Conversation model for storing chat history"""
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=False, index=True)
    thread_id = Column(String(255), nullable=False, index=True)
    
    # Conversation metadata
    title = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    language = Column(String(10), nullable=True)
    
    # Conversation data
    messages = Column(JSON, default=list, nullable=False)
    conversation_metadata = Column(JSON, default=dict, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Conversation state
    is_active = Column(Boolean, default=True, nullable=False)
    message_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    session = relationship("Session", back_populates="conversations")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, thread_id='{self.thread_id}', user_id={self.user_id})>"

class ToolUsage(Base):
    """Model for tracking tool usage and performance"""
    __tablename__ = "tool_usage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=True, index=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id'), nullable=True, index=True)
    
    # Tool information
    tool_name = Column(String(100), nullable=False, index=True)
    tool_version = Column(String(50), nullable=True)
    agent_name = Column(String(100), nullable=True, index=True)
    
    # Usage data
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    execution_time = Column(Integer, nullable=True)  # milliseconds
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User")
    session = relationship("Session")
    conversation = relationship("Conversation")
    
    def __repr__(self):
        return f"<ToolUsage(id={self.id}, tool_name='{self.tool_name}', success={self.success})>"

class APIUsage(Base):
    """Model for tracking external API usage and costs"""
    __tablename__ = "api_usage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=True, index=True)
    
    # API information
    service_name = Column(String(100), nullable=False, index=True)  # openai, google, etc.
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)  # GET, POST, etc.
    
    # Usage metrics
    request_tokens = Column(Integer, nullable=True)
    response_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    estimated_cost = Column(String(20), nullable=True)  # Store as string to avoid float precision issues
    
    # Request/Response data (truncated for storage)
    request_data = Column(JSON, nullable=True)
    response_data = Column(JSON, nullable=True)
    
    # Performance metrics
    response_time = Column(Integer, nullable=True)  # milliseconds
    success = Column(Boolean, nullable=False)
    status_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User")
    session = relationship("Session")
    
    def __repr__(self):
        return f"<APIUsage(id={self.id}, service='{self.service_name}', success={self.success})>"

class SystemLog(Base):
    """Model for storing system logs and events"""
    __tablename__ = "system_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Log information
    level = Column(String(20), nullable=False, index=True)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    logger_name = Column(String(100), nullable=False, index=True)
    message = Column(Text, nullable=False)
    
    # Context information
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=True, index=True)
    request_id = Column(String(100), nullable=True, index=True)
    
    # Additional data
    extra_data = Column(JSON, default=dict, nullable=False)
    exception_info = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)
    
    # Source information
    module = Column(String(100), nullable=True)
    function = Column(String(100), nullable=True)
    line_number = Column(Integer, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User")
    session = relationship("Session")
    
    def __repr__(self):
        return f"<SystemLog(id={self.id}, level='{self.level}', logger='{self.logger_name}')>"
