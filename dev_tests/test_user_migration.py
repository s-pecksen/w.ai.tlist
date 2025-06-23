#!/usr/bin/env python3
"""
Test script for User database migration.
Tests user operations with SQLite database.
"""

import os
import sys
import json
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.config import Config
from src.repositories.user_repository import UserRepository
from src.models.user import User
from src.models.provider import db
from app import app

def test_user_operations():
    """Test user CRUD operations."""
    print("🧪 Testing User Database Operations")
    print("=" * 50)
    
    # Initialize repository
    user_repo = UserRepository()
    
    # Test data
    test_user_data = {
        "username": "test_user",
        "email": "test@example.com",
        "clinic_name": "Test Dental Clinic",
        "user_name_for_message": "Dr. Test",
        "appointment_types": json.dumps(["Cleaning", "Checkup"]),
        "appointment_types_data": json.dumps([{"name": "Cleaning", "duration": 60}, {"name": "Checkup", "duration": 30}])
    }
    
    print(f"📊 Database Mode: SQLite")
    print(f"📁 Database URL: {Config.LOCAL_DATABASE_URL}")
    print()
    
    # Test 1: Create user
    print("1️⃣ Creating test user...")
    try:
        user = user_repo.create(test_user_data)
        if user:
            print(f"✅ User created successfully: {user.username} (ID: {user.id})")
            user_id = user.id
        else:
            print("❌ Failed to create user")
            return False
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return False
    
    # Test 2: Get user by ID
    print("\n2️⃣ Getting user by ID...")
    try:
        retrieved_user = user_repo.get_by_id(user_id)
        if retrieved_user:
            print(f"✅ User retrieved: {retrieved_user.username}")
        else:
            print("❌ Failed to retrieve user by ID")
            return False
    except Exception as e:
        print(f"❌ Error retrieving user by ID: {e}")
        return False
    
    # Test 3: Get user by username
    print("\n3️⃣ Getting user by username...")
    try:
        user_by_username = user_repo.get_by_username("test_user")
        if user_by_username:
            print(f"✅ User found by username: {user_by_username.username}")
        else:
            print("❌ Failed to find user by username")
            return False
    except Exception as e:
        print(f"❌ Error retrieving user by username: {e}")
        return False
    
    # Test 4: Get user by email
    print("\n4️⃣ Getting user by email...")
    try:
        user_by_email = user_repo.get_by_email("test@example.com")
        if user_by_email:
            print(f"✅ User found by email: {user_by_email.email}")
        else:
            print("❌ Failed to find user by email")
            return False
    except Exception as e:
        print(f"❌ Error retrieving user by email: {e}")
        return False
    
    # Test 5: Update user
    print("\n5️⃣ Updating user...")
    try:
        update_data = {
            "clinic_name": "Updated Dental Clinic",
            "user_name_for_message": "Dr. Updated"
        }
        updated_user = user_repo.update(user_id, update_data)
        if updated_user:
            print(f"✅ User updated: {updated_user.clinic_name}")
        else:
            print("❌ Failed to update user")
            return False
    except Exception as e:
        print(f"❌ Error updating user: {e}")
        return False
    
    # Test 6: Get all users
    print("\n6️⃣ Getting all users...")
    try:
        all_users = user_repo.get_all()
        print(f"✅ Found {len(all_users)} users")
        for user in all_users:
            print(f"   - {user.username} ({user.email})")
    except Exception as e:
        print(f"❌ Error getting all users: {e}")
        return False
    
    # Test 7: Delete user
    print("\n7️⃣ Deleting test user...")
    try:
        success = user_repo.delete(user_id)
        if success:
            print("✅ User deleted successfully")
        else:
            print("❌ Failed to delete user")
            return False
    except Exception as e:
        print(f"❌ Error deleting user: {e}")
        return False
    
    # Test 8: Verify deletion
    print("\n8️⃣ Verifying deletion...")
    try:
        deleted_user = user_repo.get_by_id(user_id)
        if deleted_user is None:
            print("✅ User successfully deleted (not found)")
        else:
            print("❌ User still exists after deletion")
            return False
    except Exception as e:
        print(f"❌ Error verifying deletion: {e}")
        return False
    
    print("\n🎉 All user tests passed!")
    return True

def test_database_tables():
    """Test that all database tables exist."""
    print("\n🔍 Checking Database Tables")
    print("=" * 30)
    
    try:
        # Check if tables exist
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        
        required_tables = ['users', 'providers', 'patients', 'slots']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            return False
        else:
            print(f"✅ All required tables exist: {required_tables}")
            return True
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Starting User Database Migration Tests")
    print("=" * 60)
    
    # Run tests within Flask application context
    with app.app_context():
        # Test database tables
        if not test_database_tables():
            print("❌ Database table test failed")
            return False
        
        # Test user operations
        if not test_user_operations():
            print("❌ User operations test failed")
            return False
    
    print("\n🎉 All tests passed successfully!")
    print("✅ User database migration is working correctly")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 