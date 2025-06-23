#!/usr/bin/env python3
"""
Simple script to add a test provider directly to the SQLite database.
"""

import sqlite3
import uuid
from datetime import datetime

def add_test_provider():
    """Add a test provider to the SQLite database."""
    
    # Connect to the database
    conn = sqlite3.connect('../instance/waitlist.db')
    cursor = conn.cursor()
    
    # Create test provider data
    provider_id = str(uuid.uuid4())
    user_id = "test-user-123"
    first_name = "Dr. Test"
    last_initial = "S"
    created_at = datetime.utcnow()
    
    try:
        # Insert the provider
        cursor.execute("""
            INSERT INTO providers (id, user_id, first_name, last_initial, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (provider_id, user_id, first_name, last_initial, created_at))
        
        # Commit the transaction
        conn.commit()
        
        print(f"✅ Added test provider: {first_name} {last_initial}")
        print(f"   ID: {provider_id}")
        print(f"   User ID: {user_id}")
        
        # Verify it was added
        cursor.execute("SELECT * FROM providers")
        providers = cursor.fetchall()
        print(f"\n📊 Total providers in database: {len(providers)}")
        
        for provider in providers:
            print(f"   - {provider[2]} {provider[3]} (ID: {provider[0]})")
            
    except Exception as e:
        print(f"❌ Error adding provider: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_test_provider() 