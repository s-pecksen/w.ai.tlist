#!/usr/bin/env python3
"""
Test script for ProviderRepository migration.
Tests both Supabase and SQLite implementations.
"""

import os
import sys
import requests
import json
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_supabase_providers():
    """Test provider operations with Supabase."""
    print("🧪 Testing Supabase Provider Operations...")
    
    # Test data
    test_user_id = "test-user-123"
    test_provider_data = {
        "user_id": test_user_id,
        "first_name": "Dr. Test",
        "last_initial": "S"
    }
    
    try:
        # Start the app (you'll need to do this manually)
        print("📝 Please start the app with: python app.py")
        print("📝 Make sure USE_LOCAL_DB=false in .env")
        input("Press Enter when the app is running...")
        
        base_url = "http://localhost:7860"
        
        # Test 1: Get providers (should be empty initially)
        print("\n1️⃣ Testing GET /providers...")
        response = requests.get(f"{base_url}/providers")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ GET /providers works")
        else:
            print("   ❌ GET /providers failed")
            return False
        
        # Test 2: Add a provider
        print("\n2️⃣ Testing POST /add_provider...")
        response = requests.post(f"{base_url}/add_provider", data=test_provider_data)
        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 302]:  # 302 is redirect after POST
            print("   ✅ POST /add_provider works")
        else:
            print("   ❌ POST /add_provider failed")
            return False
        
        # Test 3: Get providers again (should have the new provider)
        print("\n3️⃣ Testing GET /providers (after adding)...")
        response = requests.get(f"{base_url}/providers")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ GET /providers after adding works")
        else:
            print("   ❌ GET /providers after adding failed")
            return False
        
        print("\n✅ Supabase provider tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Supabase: {e}")
        return False

def test_sqlite_providers():
    """Test provider operations with SQLite."""
    print("\n🧪 Testing SQLite Provider Operations...")
    
    # Test data
    test_user_id = "test-user-456"
    test_provider_data = {
        "user_id": test_user_id,
        "first_name": "Dr. Local",
        "last_initial": "L"
    }
    
    try:
        # Update .env to use local database
        print("📝 Switching to local database...")
        with open('.env', 'r') as f:
            env_content = f.read()
        
        env_content = env_content.replace('USE_LOCAL_DB=false', 'USE_LOCAL_DB=true')
        
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print("📝 Please restart the app with: python app.py")
        print("📝 Make sure USE_LOCAL_DB=true in .env")
        input("Press Enter when the app is running with local DB...")
        
        base_url = "http://localhost:7860"
        
        # Test 1: Get providers (should be empty initially)
        print("\n1️⃣ Testing GET /providers (SQLite)...")
        response = requests.get(f"{base_url}/providers")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ GET /providers works with SQLite")
        else:
            print("   ❌ GET /providers failed with SQLite")
            return False
        
        # Test 2: Add a provider
        print("\n2️⃣ Testing POST /add_provider (SQLite)...")
        response = requests.post(f"{base_url}/add_provider", data=test_provider_data)
        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 302]:  # 302 is redirect after POST
            print("   ✅ POST /add_provider works with SQLite")
        else:
            print("   ❌ POST /add_provider failed with SQLite")
            return False
        
        # Test 3: Get providers again (should have the new provider)
        print("\n3️⃣ Testing GET /providers (SQLite, after adding)...")
        response = requests.get(f"{base_url}/providers")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ GET /providers after adding works with SQLite")
        else:
            print("   ❌ GET /providers after adding failed with SQLite")
            return False
        
        print("\n✅ SQLite provider tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing SQLite: {e}")
        return False

def cleanup():
    """Clean up test data and restore .env."""
    print("\n🧹 Cleaning up...")
    
    # Restore .env to Supabase
    with open('.env', 'r') as f:
        env_content = f.read()
    
    env_content = env_content.replace('USE_LOCAL_DB=true', 'USE_LOCAL_DB=false')
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Cleanup completed")

def main():
    """Run all tests."""
    print("🚀 Provider Migration Test Suite")
    print("=" * 50)
    
    # Test Supabase
    supabase_success = test_supabase_providers()
    
    # Test SQLite
    sqlite_success = test_sqlite_providers()
    
    # Cleanup
    cleanup()
    
    # Results
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"   Supabase: {'✅ PASS' if supabase_success else '❌ FAIL'}")
    print(f"   SQLite:   {'✅ PASS' if sqlite_success else '❌ FAIL'}")
    
    if supabase_success and sqlite_success:
        print("\n🎉 All tests passed! Provider migration is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main() 