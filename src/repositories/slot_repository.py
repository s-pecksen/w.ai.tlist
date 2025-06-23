from typing import List, Dict, Any, Optional
from src.repositories.base_repository import BaseRepository
from src.database_factory import DatabaseFactory
import logging

logger = logging.getLogger(__name__)

class SlotRepository(BaseRepository):
    """Repository for slot-related database operations."""
    
    def __init__(self, app=None):
        super().__init__("cancelled_slots")
        self.database = DatabaseFactory.get_database(app)
    
    def get_available_slots(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all available slots for a user."""
        try:
            slots = self.database.get_slots(user_id)
            return [s for s in slots if s.get('status') == 'available']
        except Exception as e:
            logger.error(f"Error getting available slots for user {user_id}: {e}")
            return []
    
    def get_by_status(self, user_id: str, status: str) -> List[Dict[str, Any]]:
        """Get slots by status."""
        try:
            slots = self.database.get_slots(user_id)
            return [s for s in slots if s.get('status') == status]
        except Exception as e:
            logger.error(f"Error getting slots by status {status} for user {user_id}: {e}")
            return []
    
    def update_status(self, slot_id: str, user_id: str, status: str, proposed_patient_id: str = None, proposed_patient_name: str = None) -> bool:
        """Update slot status and proposed patient."""
        data = {"status": status}
        if proposed_patient_id is not None:
            data["proposed_patient_id"] = proposed_patient_id
        if proposed_patient_name is not None:
            data["proposed_patient_name"] = proposed_patient_name
        return self.database.update_slot(slot_id, user_id, data)
    
    def get_by_provider(self, user_id: str, provider_id: str) -> List[Dict[str, Any]]:
        """Get slots by provider."""
        try:
            slots = self.database.get_slots(user_id)
            return [s for s in slots if s.get('provider') == provider_id]
        except Exception as e:
            logger.error(f"Error getting slots by provider {provider_id} for user {user_id}: {e}")
            return []
    
    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new slot."""
        return self.database.create_slot(data)
    
    def update(self, record_id: str, user_id: str, data: Dict[str, Any]) -> bool:
        """Update a slot."""
        return self.database.update_slot(record_id, user_id, data) 