from typing import List, Dict, Any, Optional
from src.repositories.base_repository import BaseRepository
from src.database_factory import DatabaseFactory
import logging

logger = logging.getLogger(__name__)

class PatientRepository(BaseRepository):
    """Repository for patient-related database operations."""
    
    def __init__(self, app=None):
        super().__init__("patients")
        self.database = DatabaseFactory.get_database(app)
    
    def get_waitlist(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all patients in the waitlist for a user."""
        return self.database.get_patients(user_id)
    
    def get_by_status(self, user_id: str, status: str) -> List[Dict[str, Any]]:
        """Get patients by status."""
        try:
            patients = self.database.get_patients(user_id)
            return [p for p in patients if p.get('status') == status]
        except Exception as e:
            logger.error(f"Error getting patients by status {status} for user {user_id}: {e}")
            return []
    
    def update_status(self, patient_id: str, user_id: str, status: str, proposed_slot_id: str = None) -> bool:
        """Update patient status and proposed slot."""
        data = {"status": status}
        if proposed_slot_id is not None:
            data["proposed_slot_id"] = proposed_slot_id
        return self.database.update_patient(patient_id, user_id, data)
    
    def bulk_create(self, patients_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create multiple patients at once."""
        try:
            created_patients = []
            for patient_data in patients_data:
                patient = self.database.create_patient(patient_data)
                if patient:
                    created_patients.append(patient)
            return created_patients
        except Exception as e:
            logger.error(f"Error bulk creating patients: {e}")
            return []
    
    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new patient."""
        return self.database.create_patient(data)
    
    def update(self, record_id: str, user_id: str, data: Dict[str, Any]) -> bool:
        """Update a patient."""
        return self.database.update_patient(record_id, user_id, data) 