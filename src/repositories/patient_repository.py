from typing import List, Dict, Any, Optional
from src.repositories.base_repository import BaseRepository
from src.database import get_supabase_client
import logging

logger = logging.getLogger(__name__)

class PatientRepository(BaseRepository):
    """Repository for patient-related database operations."""
    
    def __init__(self):
        super().__init__("patients")
    
    def get_waitlist(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all patients in the waitlist for a user."""
        try:
            response = self.supabase.table(self.table_name).select("*").eq("user_id", user_id).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting waitlist for user {user_id}: {e}")
            return []
    
    def get_by_status(self, user_id: str, status: str) -> List[Dict[str, Any]]:
        """Get patients by status."""
        try:
            response = self.supabase.table(self.table_name).select("*").eq("user_id", user_id).eq("status", status).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting patients by status {status} for user {user_id}: {e}")
            return []
    
    def update_status(self, patient_id: str, user_id: str, status: str, proposed_slot_id: str = None) -> bool:
        """Update patient status and proposed slot."""
        data = {"status": status}
        if proposed_slot_id is not None:
            data["proposed_slot_id"] = proposed_slot_id
        return self.update(patient_id, user_id, data)
    
    def bulk_create(self, patients_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create multiple patients at once."""
        try:
            response = self.supabase.table(self.table_name).insert(patients_data).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error bulk creating patients: {e}")
            return [] 