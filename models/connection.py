# models/connection.py
"""
Database connection and session management for Jarvis-MK42
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager, asynccontextmanager
from typing import Generator, Optional
import logging
import os

from config.settings import get_settings
from .database import Base
from utils.exceptions import DatabaseError
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Global variables for engine and session factory
_engine = None
_SessionLocal = None

def create_database_engine():
    """Create and configure the database engine"""
    global _engine
    
    if _engine is not None:
        return _engine
    
    settings = get_settings()
    database_url = settings.database.url
    
    # Engine configuration
    engine_kwargs = {
        "echo": settings.database.echo,
        "pool_pre_ping": True,  # Validate connections before use
    }
    
    # SQLite specific configuration
    if database_url.startswith("sqlite"):
        engine_kwargs.update({
            "poolclass": StaticPool,
            "connect_args": {
                "check_same_thread": False,
                "timeout": 20
            }
        })
    else:
        # PostgreSQL/other database configuration
        engine_kwargs.update({
            "pool_size": settings.database.pool_size,
            "max_overflow": settings.database.max_overflow,
            "pool_timeout": 30,
            "pool_recycle": 3600,  # Recycle connections every hour
        })
    
    try:
        _engine = create_engine(database_url, **engine_kwargs)
        
        # Add connection event listeners
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            if database_url.startswith("sqlite"):
                cursor = dbapi_connection.cursor()
                # Enable foreign key constraints
                cursor.execute("PRAGMA foreign_keys=ON")
                # Set WAL mode for better concurrency
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()
        
        logger.info(f"Database engine created successfully for {database_url}")
        return _engine
        
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise DatabaseError(f"Failed to create database engine: {str(e)}")

def create_session_factory():
    """Create the session factory"""
    global _SessionLocal
    
    if _SessionLocal is not None:
        return _SessionLocal
    
    engine = create_database_engine()
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    logger.info("Database session factory created successfully")
    return _SessionLocal

def create_tables():
    """Create all database tables"""
    try:
        engine = create_database_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise DatabaseError(f"Failed to create database tables: {str(e)}")

def drop_tables():
    """Drop all database tables (use with caution!)"""
    try:
        engine = create_database_engine()
        Base.metadata.drop_all(bind=engine)
        logger.warning("All database tables dropped")
    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise DatabaseError(f"Failed to drop database tables: {str(e)}")

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions
    
    Usage:
        with get_db_session() as db:
            user = db.query(User).first()
    """
    SessionLocal = create_session_factory()
    session = SessionLocal()
    
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()

def get_db() -> Session:
    """
    Dependency for getting database sessions (for FastAPI/dependency injection)
    
    Usage in FastAPI:
        def get_user(db: Session = Depends(get_db)):
            return db.query(User).first()
    """
    SessionLocal = create_session_factory()
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

class DatabaseManager:
    """Database manager class for more advanced operations"""
    
    def __init__(self):
        self.engine = create_database_engine()
        self.SessionLocal = create_session_factory()
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Get a database session"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise
        finally:
            session.close()
    
    def health_check(self) -> bool:
        """Check if database connection is healthy"""
        try:
            with self.session() as db:
                db.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def initialize_database(self, create_admin_user: bool = True):
        """Initialize the database with tables and optional admin user"""
        try:
            # Create tables
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database initialized successfully")
            
            # Create admin user if requested
            if create_admin_user:
                self.create_admin_user()
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Failed to initialize database: {str(e)}")
    
    def create_admin_user(self):
        """Create default admin user if it doesn't exist"""
        try:
            from .database import User
            import bcrypt
            
            settings = get_settings()
            admin_password_hash = settings.security.get_user_password_hash("admin")
            
            if not admin_password_hash:
                logger.warning("No admin password hash found in environment variables")
                return
            
            with self.session() as db:
                # Check if admin user exists
                existing_admin = db.query(User).filter(User.username == "admin").first()
                
                if not existing_admin:
                    admin_user = User(
                        username="admin",
                        password_hash=admin_password_hash,
                        full_name="Administrator",
                        is_admin=True,
                        is_active=True
                    )
                    db.add(admin_user)
                    db.commit()
                    logger.info("Admin user created successfully")
                else:
                    logger.info("Admin user already exists")
                    
        except Exception as e:
            logger.error(f"Failed to create admin user: {e}")
            # Don't raise here as this is not critical for startup

# Global database manager instance
db_manager = DatabaseManager()

def init_database():
    """Initialize the database (call this at application startup)"""
    try:
        db_manager.initialize_database()
        logger.info("Database initialization completed")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

def close_database():
    """Close database connections (call this at application shutdown)"""
    global _engine
    if _engine:
        _engine.dispose()
        logger.info("Database connections closed")
