import os
import pytest
from dotenv import load_dotenv
from src.database import DatabaseManager, configure_encryption
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def db_manager():
    """Create a database manager for testing."""
    load_dotenv()
    cipher_suite = configure_encryption()
    if not cipher_suite:
        pytest.fail("Failed to configure encryption")
    return DatabaseManager("test_user", cipher_suite)

def test_provider_operations(db_manager):
    """Test provider-related database operations."""
    # Add provider
    provider_added = db_manager.add_provider("Test", "D")
    assert provider_added, "Failed to add provider"
    
    # Get providers
    providers = db_manager.get_providers()
    assert len(providers) > 0, "No providers found"
    logger.info(f"Found {len(providers)} providers")
    
    # Clean up
    provider_id = providers[0]['id']
    db_manager.remove_provider(provider_id)

def test_slot_operations(db_manager):
    """Test slot-related database operations."""
    # Add provider first
    db_manager.add_provider("Test", "D")
    providers = db_manager.get_providers()
    provider_id = providers[0]['id']
    
    # Add slot
    slot_added = db_manager.add_cancelled_slot(
        provider_id=provider_id,
        date="2024-03-20",
        time="09:00",
        duration=30,
        notes="Test slot"
    )
    assert slot_added, "Failed to add slot"
    
    # Get slots
    slots = db_manager.get_cancelled_slots()
    assert len(slots) > 0, "No slots found"
    logger.info(f"Found {len(slots)} slots")
    
    # Clean up
    slot_id = slots[0]['id']
    db_manager.remove_cancelled_slot(slot_id)
    db_manager.remove_provider(provider_id)

def test_patient_operations(db_manager):
    """Test patient-related database operations."""
    # Add patient
    patient_added = db_manager.add_patient(
        name="Test Patient",
        phone="123-456-7890",
        email="test@example.com",
        reason="Test appointment",
        urgency="medium",
        appointment_type="checkup",
        duration=30,
        provider="no preference"
    )
    assert patient_added, "Failed to add patient"
    
    # Get patients
    patients = db_manager.get_patients()
    assert len(patients) > 0, "No patients found"
    logger.info(f"Found {len(patients)} patients")
    
    # Clean up
    patient_id = patients[0]['id']
    db_manager.remove_patient(patient_id)

def test_slot_proposal_flow(db_manager):
    """Test the complete slot proposal flow."""
    # Setup test data
    db_manager.add_provider("Test", "D")
    providers = db_manager.get_providers()
    provider_id = providers[0]['id']
    
    db_manager.add_cancelled_slot(
        provider_id=provider_id,
        date="2024-03-20",
        time="09:00",
        duration=30
    )
    slots = db_manager.get_cancelled_slots()
    slot_id = slots[0]['id']
    
    db_manager.add_patient(
        name="Test Patient",
        phone="123-456-7890",
        email="test@example.com",
        reason="Test appointment",
        urgency="medium",
        appointment_type="checkup",
        duration=30
    )
    patients = db_manager.get_patients()
    patient_id = patients[0]['id']
    
    # Test proposal flow
    slot_marked = db_manager.mark_slot_as_pending(slot_id, patient_id, "Test Patient")
    assert slot_marked, "Failed to mark slot as pending"
    
    patient_marked = db_manager.mark_patient_as_pending(patient_id, slot_id)
    assert patient_marked, "Failed to mark patient as pending"
    
    # Test cancellation
    slot_cancelled = db_manager.cancel_slot_proposal(slot_id)
    assert slot_cancelled, "Failed to cancel slot proposal"
    
    patient_cancelled = db_manager.cancel_patient_proposal(patient_id)
    assert patient_cancelled, "Failed to cancel patient proposal"
    
    # Clean up
    db_manager.remove_patient(patient_id)
    db_manager.remove_cancelled_slot(slot_id)
    db_manager.remove_provider(provider_id) 