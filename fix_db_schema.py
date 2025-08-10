#!/usr/bin/env python3

import sqlite3

def add_missing_column():
    conn = sqlite3.connect('chainlit.db')
    cursor = conn.cursor()
    
    try:
        # Add the missing defaultOpen column
        print("Adding defaultOpen column to steps table...")
        cursor.execute("ALTER TABLE steps ADD COLUMN defaultOpen INTEGER DEFAULT 0")
        conn.commit()
        print("Successfully added defaultOpen column")
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(steps)")
        columns = cursor.fetchall()
        print(f"Table now has {len(columns)} columns")
        
        # Check if defaultOpen is now present
        column_names = [row[1] for row in columns]
        if 'defaultOpen' in column_names:
            print("✓ defaultOpen column is now present")
        else:
            print("✗ defaultOpen column still missing")
            
    except sqlite3.Error as e:
        print(f"Error adding column: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_missing_column()
