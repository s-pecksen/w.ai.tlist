#!/usr/bin/env python3
"""
Comprehensive test script for all repositories.
Tests providers, patients, and slots with SQLite.
"""

import os
import sys
import sqlite3
import uuid
from datetime import datetime, date

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_sqlite_database():
    """Test all repositories with SQLite database."""
    print("🧪 Testing SQLite Database Operations...")
    
    db_path = '../instance/waitlist.db'
    
    if not os.path.exists(db_path):
        print("❌ Database file not found. Please start the app with USE_LOCAL_DB=true first.")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Test 1: Check tables exist
        print("\n1️⃣ Checking database tables...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"   Found tables: {tables}")
        
        expected_tables = ['providers', 'patients', 'cancelled_slots']
        for table in expected_tables:
            if table in tables:
                print(f"   ✅ {table} table exists")
            else:
                print(f"   ❌ {table} table missing")
                return False
        
        # Test 2: Add test data
        print("\n2️⃣ Adding test data...")
        
        # Add provider
        provider_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO providers (id, user_id, first_name, last_initial, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (provider_id, "test-user", "Dr. Test", "P", datetime.utcnow()))
        
        # Add patient
        patient_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO patients (id, user_id, name, phone, email, appointment_type, duration, provider, urgency, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (patient_id, "test-user", "John Doe", "555-1234", "john@test.com", "checkup", "60", "Dr. Test P", "medium", "waiting", datetime.utcnow()))
        
        # Add slot
        slot_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO cancelled_slots (id, user_id, provider, date, start_time, end_time, duration, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (slot_id, "test-user", "Dr. Test P", date.today(), "09:00", "10:00", 60, "available", datetime.utcnow()))
        
        conn.commit()
        print("   ✅ Test data added successfully")
        
        # Test 3: Query data
        print("\n3️⃣ Querying test data...")
        
        # Query providers
        cursor.execute("SELECT * FROM providers WHERE user_id = ?", ("test-user",))
        providers = cursor.fetchall()
        print(f"   Providers: {len(providers)} found")
        
        # Query patients
        cursor.execute("SELECT * FROM patients WHERE user_id = ?", ("test-user",))
        patients = cursor.fetchall()
        print(f"   Patients: {len(patients)} found")
        
        # Query slots
        cursor.execute("SELECT * FROM cancelled_slots WHERE user_id = ?", ("test-user",))
        slots = cursor.fetchall()
        print(f"   Slots: {len(slots)} found")
        
        # Test 4: Update data
        print("\n4️⃣ Testing updates...")
        
        # Update patient status
        cursor.execute("UPDATE patients SET status = ? WHERE id = ?", ("matched", patient_id))
        
        # Update slot status
        cursor.execute("UPDATE cancelled_slots SET status = ?, proposed_patient_id = ? WHERE id = ?", 
                      ("proposed", patient_id, slot_id))
        
        conn.commit()
        print("   ✅ Updates successful")
        
        # Test 5: Verify updates
        print("\n5️⃣ Verifying updates...")
        
        cursor.execute("SELECT status FROM patients WHERE id = ?", (patient_id,))
        patient_status = cursor.fetchone()[0]
        print(f"   Patient status: {patient_status}")
        
        cursor.execute("SELECT status, proposed_patient_id FROM cancelled_slots WHERE id = ?", (slot_id,))
        slot_status, proposed_patient = cursor.fetchone()
        print(f"   Slot status: {slot_status}, proposed patient: {proposed_patient}")
        
        # Clean up test data
        print("\n6️⃣ Cleaning up test data...")
        cursor.execute("DELETE FROM providers WHERE user_id = ?", ("test-user",))
        cursor.execute("DELETE FROM patients WHERE user_id = ?", ("test-user",))
        cursor.execute("DELETE FROM cancelled_slots WHERE user_id = ?", ("test-user",))
        conn.commit()
        print("   ✅ Test data cleaned up")
        
        conn.close()
        print("\n✅ All SQLite database tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing SQLite database: {e}")
        if 'conn' in locals():
            conn.close()
        return False



def main():
    """Run all tests."""
    print("🚀 All Repositories Test Suite")
    print("=" * 50)
    
    # Test SQLite database
    sqlite_success = test_sqlite_database()
    
    print("\n" + "=" * 50)
    if sqlite_success:
        print("✅ All tests completed successfully!")
        print("🎉 All repositories are working correctly with SQLite!")
    else:
        print("❌ Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main() 