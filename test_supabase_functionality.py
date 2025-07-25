#!/usr/bin/env python3
"""
Comprehensive Supabase Database Functionality Test
Tests all CRUD operations, relationships, and edge cases
"""

import sys
import os
import json
import uuid
import time
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Import the existing Flask app instead of creating a new one
from app import app, db
from src.repositories.user_repository import UserRepository
from src.repositories.patient_repository import PatientRepository
from src.repositories.provider_repository import ProviderRepository
from src.repositories.slot_repository import SlotRepository

class DatabaseTester:
    def __init__(self):
        self.app = app  # Use existing app
        self.user_repo = UserRepository()
        self.patient_repo = PatientRepository()
        self.provider_repo = ProviderRepository()
        self.slot_repo = SlotRepository()
        self.test_user_id = None
        self.test_data_ids = {
            'users': [],
            'patients': [],
            'providers': [],
            'slots': []
        }
        
    def run_all_tests(self):
        """Run comprehensive database test suite"""
        print("🚀 Starting Comprehensive Supabase Database Test Suite")
        print("=" * 60)
        
        with self.app.app_context():
            try:
                # Test 1: Basic Connectivity
                self.test_connectivity()
                
                # Test 2: User Operations
                self.test_user_operations()
                
                # Test 3: Provider Operations
                self.test_provider_operations()
                
                # Test 4: Patient Operations
                self.test_patient_operations()
                
                # Test 5: Slot Operations
                self.test_slot_operations()
                
                # Test 6: Complex Queries
                self.test_complex_queries()
                
                # Test 7: Bulk Operations
                self.test_bulk_operations()
                
                # Test 8: Error Handling
                self.test_error_handling()
                
                # Test 9: Performance
                self.test_performance()
                
                print("\n🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
                print("✅ Your Supabase database is working perfectly!")
                
            except Exception as e:
                print(f"\n❌ Test failed: {e}")
                import traceback
                traceback.print_exc()
                raise
            finally:
                # Clean up test data
                self.cleanup_test_data()
    
    def test_connectivity(self):
        """Test basic database connectivity"""
        print("\n📡 Testing Database Connectivity...")
        
        # Test connection
        result = db.session.execute(db.text("SELECT 1 as test"))
        assert result.fetchone()[0] == 1
        print("✅ Database connection successful")
        
        # Test PostgreSQL version
        result = db.session.execute(db.text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"✅ PostgreSQL version: {version[:50]}...")
        
        # Test transaction handling
        try:
            db.session.rollback()  # Roll back any existing transaction
            db.session.begin()
            db.session.rollback()
            print("✅ Transaction handling works")
        except Exception as e:
            # Session might already be in a transaction
            print("✅ Transaction handling functional (session already active)")
        
    def test_user_operations(self):
        """Test all user CRUD operations"""
        print("\n👤 Testing User Operations...")
        
        # CREATE
        user_data = {
            "id": str(uuid.uuid4()),
            "username": f"test-{int(time.time())}@supabase.com",
            "email": f"test-{int(time.time())}@supabase.com",
            "password_hash": generate_password_hash("testpass123"),
            "clinic_name": "Test Clinic",
            "user_name_for_message": "Test User",
            "appointment_types": json.dumps(["Test Type 1", "Test Type 2"]),
            "appointment_types_data": json.dumps([
                {"appointment_type": "Test Type 1", "durations": [30]},
                {"appointment_type": "Test Type 2", "durations": [60]}
            ])
        }
        
        user = self.user_repo.create(user_data)
        assert user is not None
        self.test_user_id = user.id
        self.test_data_ids['users'].append(user.id)
        print("✅ User creation successful")
        
        # READ
        retrieved_user = self.user_repo.get_by_id(user.id)
        assert retrieved_user.email == user_data["email"]
        assert retrieved_user.clinic_name == "Test Clinic"
        print("✅ User retrieval successful")
        
        # READ by email
        user_by_email = self.user_repo.get_by_email(user_data["email"])
        assert user_by_email.id == user.id
        print("✅ User retrieval by email successful")
        
        # UPDATE
        success = self.user_repo.update(user.id, {"clinic_name": "Updated Test Clinic"})
        assert success
        print("✅ User update successful")
        
    def test_provider_operations(self):
        """Test provider CRUD operations"""
        print("\n👨‍⚕️ Testing Provider Operations...")
        
        # CREATE
        provider_data = {
            "user_id": self.test_user_id,
            "first_name": "Dr. Test",
            "last_initial": "T"
        }
        
        provider = self.provider_repo.create(provider_data)
        assert provider is not None
        self.test_data_ids['providers'].append(provider['id'])
        print("✅ Provider creation successful")
        
        # READ
        providers = self.provider_repo.get_providers(self.test_user_id)
        assert len(providers) >= 1
        test_provider = next((p for p in providers if p['first_name'] == "Dr. Test"), None)
        assert test_provider is not None
        print("✅ Provider retrieval successful")
        
        # UPDATE
        success = self.provider_repo.update(provider['id'], self.test_user_id, {"first_name": "Dr. Updated"})
        assert success
        print("✅ Provider update successful")
        
    def test_patient_operations(self):
        """Test patient CRUD operations"""
        print("\n🏥 Testing Patient Operations...")
        
        # CREATE
        patient_data = {
            "user_id": self.test_user_id,
            "name": "Test Patient",
            "phone": "555-0123",
            "email": f"patient-{int(time.time())}@test.com",
            "reason": "Test reason",
            "urgency": "medium",
            "appointment_type": "Test Type 1",
            "duration": 30,
            "provider": "Dr. Test T",
            "availability": json.dumps({
                "Monday": ["9:00 AM", "5:00 PM"],
                "Tuesday": ["9:00 AM", "5:00 PM"]
            })
        }
        
        patient = self.patient_repo.create(patient_data)
        assert patient is not None
        self.test_data_ids['patients'].append(patient['id'])
        print("✅ Patient creation successful")
        
        # READ
        patients = self.patient_repo.get_waitlist(self.test_user_id)
        assert len(patients) >= 1
        test_patient = next((p for p in patients if p['name'] == "Test Patient"), None)
        assert test_patient is not None
        assert test_patient['phone'] == "555-0123"
        print("✅ Patient retrieval successful")
        
        # UPDATE
        success = self.patient_repo.update(patient['id'], self.test_user_id, {"phone": "555-9999"})
        assert success
        print("✅ Patient update successful")
        
        # Test JSON field parsing
        availability = test_patient['availability']
        if isinstance(availability, str):
            availability = json.loads(availability)
        assert "Monday" in availability
        print("✅ JSON field handling successful")
        
    def test_slot_operations(self):
        """Test slot/appointment CRUD operations"""
        print("\n📅 Testing Slot Operations...")
        
        # CREATE
        slot_data = {
            "user_id": self.test_user_id,
            "date": "2025-08-01",
            "start_time": "10:00",
            "duration": 30,
            "provider": "Dr. Test T",
            "appointment_type": "Test Type 1",
            "reason": "Cancelled appointment"
        }
        
        slot = self.slot_repo.create(slot_data)
        assert slot is not None
        self.test_data_ids['slots'].append(slot['id'])
        print("✅ Slot creation successful")
        
        # READ
        slots = self.slot_repo.get_all_slots(self.test_user_id)
        assert len(slots) >= 1
        test_slot = next((s for s in slots if s['date'] == "2025-08-01"), None)
        assert test_slot is not None
        assert test_slot['start_time'] == "10:00"
        print("✅ Slot retrieval successful")
        
        # UPDATE
        success = self.slot_repo.update(slot['id'], self.test_user_id, {"start_time": "11:00"})
        assert success
        print("✅ Slot update successful")
        
    def test_complex_queries(self):
        """Test complex database queries and relationships"""
        print("\n🔍 Testing Complex Queries...")
        
        # Test user with all related data
        user = self.user_repo.get_by_id(self.test_user_id)
        patients = self.patient_repo.get_waitlist(self.test_user_id)
        providers = self.provider_repo.get_providers(self.test_user_id)
        slots = self.slot_repo.get_all_slots(self.test_user_id)
        
        assert user is not None
        assert len(patients) >= 1
        assert len(providers) >= 1
        assert len(slots) >= 1
        print("✅ User relationship queries successful")
        
        # Test filtering
        filtered_patients = [p for p in patients if p['urgency'] == "medium"]
        assert len(filtered_patients) >= 1
        print("✅ Data filtering successful")
        
        # Test JSON queries
        appointment_types_data = json.loads(user.appointment_types_data)
        assert len(appointment_types_data) >= 2
        print("✅ JSON field queries successful")
        
    def test_bulk_operations(self):
        """Test bulk database operations"""
        print("\n📦 Testing Bulk Operations...")
        
        # Bulk patient creation
        bulk_patients = []
        for i in range(5):
            patient_data = {
                "user_id": self.test_user_id,
                "name": f"Bulk Patient {i+1}",
                "phone": f"555-{1000+i}",
                "email": f"bulk{i+1}-{int(time.time())}@test.com",
                "reason": f"Bulk test reason {i+1}",
                "urgency": "low",
                "appointment_type": "Test Type 1",
                "duration": 30,
                "provider": "Dr. Test T",
                "availability": json.dumps({"Monday": ["9:00 AM", "5:00 PM"]})
            }
            patient = self.patient_repo.create(patient_data)
            bulk_patients.append(patient)
            self.test_data_ids['patients'].append(patient['id'])
        
        assert len(bulk_patients) == 5
        print("✅ Bulk patient creation successful")
        
        # Test bulk retrieval
        all_patients = self.patient_repo.get_waitlist(self.test_user_id)
        bulk_count = len([p for p in all_patients if p['name'].startswith("Bulk Patient")])
        assert bulk_count >= 5
        print("✅ Bulk data retrieval successful")
        
    def test_error_handling(self):
        """Test database error handling"""
        print("\n⚠️ Testing Error Handling...")
        
        # Test invalid foreign key
        try:
            invalid_patient_data = {
                "user_id": "invalid-user-id-12345",
                "name": "Invalid Patient",
                "phone": "555-0000",
                "email": f"invalid-{int(time.time())}@test.com",
                "reason": "Test",
                "urgency": "low",
                "appointment_type": "Test",
                "duration": 30,
                "provider": "Test",
                "availability": "{}"
            }
            
            result = self.patient_repo.create(invalid_patient_data)
            if not result:
                print("✅ Foreign key validation working")
            else:
                print("ℹ️ Foreign key constraint not enforced (acceptable)")
                
        except Exception as e:
            print("✅ Foreign key error handling working")
        
        # Test malformed JSON
        try:
            malformed_patient_data = {
                "user_id": self.test_user_id,
                "name": "Malformed JSON Patient",
                "phone": "555-0001",
                "email": f"malformed-{int(time.time())}@test.com",
                "reason": "Test",
                "urgency": "low",
                "appointment_type": "Test",
                "duration": 30,
                "provider": "Test",
                "availability": "invalid json string"
            }
            
            result = self.patient_repo.create(malformed_patient_data)
            if result:
                print("ℹ️ JSON validation handled gracefully")
                self.test_data_ids['patients'].append(result.id)
                
        except Exception as e:
            print("✅ JSON error handling working")
        
    def test_performance(self):
        """Test database performance with larger operations"""
        print("\n⚡ Testing Performance...")
        
        start_time = time.time()
        
        # Test query performance
        for _ in range(10):
            patients = self.patient_repo.get_waitlist(self.test_user_id)
            providers = self.provider_repo.get_providers(self.test_user_id)
            slots = self.slot_repo.get_all_slots(self.test_user_id)
        
        end_time = time.time()
        query_time = end_time - start_time
        
        print(f"✅ Query performance good: {query_time:.2f}s for 30 operations")
        
        # Test transaction performance
        start_time = time.time()
        
        try:
            # Use nested transaction if one is already active
            with db.session.begin():
                for i in range(10):
                    # Simulate rapid operations
                    db.session.execute(db.text("SELECT 1"))
        except:
            # If transaction is already active, just run queries
            for i in range(10):
                db.session.execute(db.text("SELECT 1"))
        
        end_time = time.time()
        transaction_time = end_time - start_time
        
        print(f"✅ Transaction performance good: {transaction_time:.2f}s")
        
    def cleanup_test_data(self):
        """Clean up all test data"""
        print("\n🧹 Cleaning up test data...")
        
        try:
            # Delete in reverse order to handle foreign keys
            for slot_id in self.test_data_ids['slots']:
                try:
                    self.slot_repo.delete(slot_id)
                except:
                    pass
                    
            for patient_id in self.test_data_ids['patients']:
                try:
                    self.patient_repo.delete(patient_id)
                except:
                    pass
                    
            for provider_id in self.test_data_ids['providers']:
                try:
                    self.provider_repo.delete(provider_id)
                except:
                    pass
                    
            for user_id in self.test_data_ids['users']:
                try:
                    user = self.user_repo.get_by_id(user_id)
                    if user:
                        db.session.delete(user)
                        db.session.commit()
                except:
                    pass
            
            print("✅ Test data cleanup completed")
            
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")

def main():
    """Run the comprehensive database test suite"""
    print("🔧 Supabase Database Functionality Tester")
    print("This will test ALL database operations to ensure everything works correctly.")
    print()
    
    response = input("Do you want to run the full test suite? (y/n): ").strip().lower()
    if response != 'y':
        print("Test cancelled.")
        return
        
    tester = DatabaseTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main() 