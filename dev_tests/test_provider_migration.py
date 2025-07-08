#!/usr/bin/env python3
"""
Test script for ProviderRepository.
Tests SQLite implementation.
"""

import os
import sys
import requests
import json
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))



def test_sqlite_providers():
    """Test provider operations with SQLite."""
    print("🧪 Testing SQLite Provider Operations...")
    
    # Test data
    test_user_id = "test-user-456"
    test_provider_data = {
        "user_id": test_user_id,
        "first_name": "Dr. Local",
        "last_initial": "L"
    }
    
    try:
        print("📝 Please start the app with: python app.py")
        input("Press Enter when the app is running...")
        
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



def main():
    """Run all tests."""
    print("🚀 Provider Test Suite")
    print("=" * 50)
    
    # Test SQLite
    sqlite_success = test_sqlite_providers()
    
    # Results
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"   SQLite: {'✅ PASS' if sqlite_success else '❌ FAIL'}")
    
    if sqlite_success:
        print("\n🎉 All tests passed! Provider functionality is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main() 