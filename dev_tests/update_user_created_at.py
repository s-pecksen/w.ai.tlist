#!/usr/bin/env python3
"""
Script to update the created_at date for poop@gmail.com to 2024 for testing the 30-day login conditional.
"""

import os
import sys
import sqlite3
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def update_user_created_at():
    """Update the created_at date for poop@gmail.com to 2024."""
    
    db_path = '/home/eric/Code/conscious_business_coaching/steven/WAITLYST/instance/waitlist.db'
    
    if not os.path.exists(db_path):
        print("❌ Database file not found. Please start the app first.")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id, email, created_at FROM users WHERE email = ?", ("poop@gmail.com",))
        user = cursor.fetchone()
        
        if not user:
            print("❌ User poop@gmail.com not found in database.")
            return False
        
        user_id, email, current_created_at = user
        print(f"📊 Found user: {email}")
        print(f"   Current created_at: {current_created_at}")
        
        # Set created_at to January 1, 2024
        new_created_at = datetime(2024, 1, 1, 12, 0, 0)
        
        # Update the created_at field
        cursor.execute("UPDATE users SET created_at = ? WHERE email = ?", (new_created_at, email))
        conn.commit()
        
        print(f"✅ Updated created_at to: {new_created_at}")
        
        # Verify the update
        cursor.execute("SELECT id, email, created_at FROM users WHERE email = ?", (email,))
        updated_user = cursor.fetchone()
        print(f"   Verified created_at: {updated_user[2]}")
        
        # Calculate days since creation
        days_since_creation = (datetime.utcnow() - new_created_at).days
        print(f"   Days since creation: {days_since_creation}")
        print(f"   Within 30 days: {days_since_creation < 30}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating user: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🔄 Updating created_at for poop@gmail.com to 2024...")
    success = update_user_created_at()
    if success:
        print("✅ Update completed successfully!")
        print("\n📝 Now you can test the login with poop@gmail.com:")
        print("   - The user should be denied login (trial expired)")
        print("   - Unless they have an active Stripe subscription")
    else:
        print("❌ Update failed!") 