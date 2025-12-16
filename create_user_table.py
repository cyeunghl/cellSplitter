#!/usr/bin/env python3
"""Script to manually create the user table if it doesn't exist."""

import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app import app, db
from sqlalchemy import inspect, text

with app.app_context():
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()
    print(f"Existing tables: {existing_tables}")
    
    if "user" not in existing_tables:
        print("Creating user table...")
        with db.engine.begin() as connection:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS user (
                    id INTEGER NOT NULL PRIMARY KEY,
                    email VARCHAR(120) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at DATETIME NOT NULL
                )
            """))
        print("User table created!")
        
        # Verify it was created
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        print(f"Tables after creation: {existing_tables}")
    else:
        print("User table already exists.")

