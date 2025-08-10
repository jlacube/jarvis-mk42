#!/usr/bin/env python3

import sqlite3

def check_schema():
    conn = sqlite3.connect('chainlit.db')
    cursor = conn.cursor()
    
    # Check steps table schema
    cursor.execute("PRAGMA table_info(steps)")
    steps_columns = cursor.fetchall()
    
    print("Current steps table columns:")
    for row in steps_columns:
        print(f"  {row[1]} ({row[2]})")
    
    print(f"\nTotal columns: {len(steps_columns)}")
    
    # Check what columns are expected by looking at the error
    expected_columns = [
        'name', 'type', 'id', 'threadId', 'parentId', 'streaming', 'metadata',
        'tags', 'input', 'isError', 'output', 'createdAt', 'start', 'defaultOpen',
        'showInput', 'generation', 'end', 'language'
    ]
    
    existing_column_names = [row[1] for row in steps_columns]
    missing_columns = [col for col in expected_columns if col not in existing_column_names]
    
    if missing_columns:
        print(f"\nMissing columns: {', '.join(missing_columns)}")
    else:
        print("\nAll expected columns are present")
    
    conn.close()

if __name__ == "__main__":
    check_schema()
