from typing import List, Dict, Any, Optional
from src.repositories.base_repository import BaseRepository
from src.database import get_supabase_client
import logging

logger = logging.getLogger(__name__)

class SlotRepository(BaseRepository):
    """Repository for slot-related database operations."""
    
    def __init__(self):
        super().__init__("cancelled_slots")
    
    def get_available_slots(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all available slots for a user."""
        try:
            response = self.supabase.table(self.table_name).select("*").eq("user_id", user_id).eq("status", "available").execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting available slots for user {user_id}: {e}")
            return []
    
    def get_by_status(self, user_id: str, status: str) -> List[Dict[str, Any]]:
        """Get slots by status."""
        try:
            response = self.supabase.table(self.table_name).select("*").eq("user_id", user_id).eq("status", status).execute()
            return response.data or []
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
        return self.update(slot_id, user_id, data)
    
    def get_by_provider(self, user_id: str, provider_id: str) -> List[Dict[str, Any]]:
        """Get slots by provider."""
        try:
            response = self.supabase.table(self.table_name).select("*").eq("user_id", user_id).eq("provider", provider_id).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting slots by provider {provider_id} for user {user_id}: {e}")
            return [] 