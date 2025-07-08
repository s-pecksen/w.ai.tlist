#!/usr/bin/env python3
"""
Quick test script for provider endpoints.
Tests SQLite implementation.
"""

import os
import sys
import requests
import json
from datetime import datetime

def test_provider_endpoints():
    """Test provider endpoints directly."""
    print("🧪 Testing Provider Endpoints...")
    
    base_url = "http://localhost:7860"
    
    # Test data
    test_provider_data = {
        "user_id": "test-user-123",
        "first_name": "Dr. Test",
        "last_initial": "S"
    }
    
    try:
        # Test 1: Get providers (should work)
        print("\n1️⃣ Testing GET /providers...")
        response = requests.get(f"{base_url}/providers")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ GET /providers works")
        else:
            print(f"   ❌ GET /providers failed: {response.text}")
            return False
        
        # Test 2: Add a provider
        print("\n2️⃣ Testing POST /add_provider...")
        response = requests.post(f"{base_url}/add_provider", data=test_provider_data)
        print(f"   Status: {response.status_code}")
        if response.status_code in [200, 302]:  # 302 is redirect after POST
            print("   ✅ POST /add_provider works")
        else:
            print(f"   ❌ POST /add_provider failed: {response.text}")
            return False
        
        # Test 3: Get providers again (should have the new provider)
        print("\n3️⃣ Testing GET /providers (after adding)...")
        response = requests.get(f"{base_url}/providers")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ GET /providers after adding works")
        else:
            print(f"   ❌ GET /providers after adding failed: {response.text}")
            return False
        
        print("\n✅ Provider endpoint tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing endpoints: {e}")
        return False



def main():
    """Run tests."""
    print("🚀 Quick Provider Test")
    print("=" * 30)
    
    # Test current endpoints
    success = test_provider_endpoints()
    
    print("\n" + "=" * 30)
    if success:
        print("✅ Tests completed successfully!")
    else:
        print("❌ Some tests failed.")

if __name__ == "__main__":
    main() 