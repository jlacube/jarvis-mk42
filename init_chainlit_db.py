#!/usr/bin/env python3
"""
Initialize Chainlit SQLAlchemy data layer database schema
"""

import sqlite3
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_chainlit_schema():
    """Create the required tables for Chainlit SQLAlchemy data layer"""
    
    db_path = "chainlit.db"
    
    # SQL schema for Chainlit data layer (adapted for SQLite)
    schema_sql = """
    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        "id" TEXT PRIMARY KEY,
        "identifier" TEXT NOT NULL UNIQUE,
        "metadata" TEXT NOT NULL,
        "createdAt" TEXT
    );

    -- Threads table
    CREATE TABLE IF NOT EXISTS threads (
        "id" TEXT PRIMARY KEY,
        "createdAt" TEXT,
        "name" TEXT,
        "userId" TEXT,
        "userIdentifier" TEXT,
        "tags" TEXT,
        "metadata" TEXT,
        FOREIGN KEY ("userId") REFERENCES users("id") ON DELETE CASCADE
    );

    -- Steps table
    CREATE TABLE IF NOT EXISTS steps (
        "id" TEXT PRIMARY KEY,
        "name" TEXT NOT NULL,
        "type" TEXT NOT NULL,
        "threadId" TEXT NOT NULL,
        "parentId" TEXT,
        "streaming" INTEGER NOT NULL,
        "waitForAnswer" INTEGER,
        "isError" INTEGER,
        "metadata" TEXT,
        "tags" TEXT,
        "input" TEXT,
        "output" TEXT,
        "createdAt" TEXT,
        "command" TEXT,
        "start" TEXT,
        "end" TEXT,
        "generation" TEXT,
        "showInput" TEXT,
        "language" TEXT,
        "indent" INTEGER,
        FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
    );

    -- Elements table
    CREATE TABLE IF NOT EXISTS elements (
        "id" TEXT PRIMARY KEY,
        "threadId" TEXT,
        "type" TEXT,
        "url" TEXT,
        "chainlitKey" TEXT,
        "name" TEXT NOT NULL,
        "display" TEXT,
        "objectKey" TEXT,
        "size" TEXT,
        "page" INTEGER,
        "language" TEXT,
        "forId" TEXT,
        "mime" TEXT,
        "props" TEXT,
        FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
    );

    -- Feedbacks table
    CREATE TABLE IF NOT EXISTS feedbacks (
        "id" TEXT PRIMARY KEY,
        "forId" TEXT NOT NULL,
        "threadId" TEXT NOT NULL,
        "value" INTEGER NOT NULL,
        "comment" TEXT,
        FOREIGN KEY ("threadId") REFERENCES threads("id") ON DELETE CASCADE
    );
    """
    
    try:
        # Connect to database
        logger.info(f"Connecting to database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check existing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = cursor.fetchall()
        logger.info(f"Existing tables: {[table[0] for table in existing_tables]}")
        
        # Execute schema creation
        logger.info("Creating Chainlit database schema...")
        cursor.executescript(schema_sql)
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        all_tables = cursor.fetchall()
        logger.info(f"Tables after schema creation: {[table[0] for table in all_tables]}")
        
        # Commit changes
        conn.commit()
        logger.info("Chainlit database schema created successfully!")
        
        # Show table structures for verification
        for table_name in ['users', 'threads', 'steps', 'elements', 'feedbacks']:
            try:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                logger.info(f"Table '{table_name}' structure: {len(columns)} columns")
            except sqlite3.Error as e:
                logger.warning(f"Could not get info for table {table_name}: {e}")
        
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False
    finally:
        if conn:
            conn.close()
    
    return True

if __name__ == "__main__":
    success = create_chainlit_schema()
    if success:
        print("✅ Chainlit database schema initialized successfully!")
        print("The application should now be able to handle user authentication and session persistence.")
    else:
        print("❌ Failed to initialize Chainlit database schema.")
