from typing import List, Dict, Any, Optional
from src.database import get_supabase_client
import logging

logger = logging.getLogger(__name__)

class BaseRepository:
    """Base repository class for common database operations."""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.supabase = get_supabase_client()
    
    def get_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all records for a specific user."""
        try:
            response = self.supabase.table(self.table_name).select("*").eq("user_id", user_id).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting {self.table_name} for user {user_id}: {e}")
            return []
    
    def get_by_id(self, record_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a single record by ID and user ID."""
        try:
            response = self.supabase.table(self.table_name).select("*").eq("id", record_id).eq("user_id", user_id).single().execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting {self.table_name} {record_id}: {e}")
            return None
    
    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new record."""
        try:
            response = self.supabase.table(self.table_name).insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating {self.table_name}: {e}")
            return None
    
    def update(self, record_id: str, user_id: str, data: Dict[str, Any]) -> bool:
        """Update a record."""
        try:
            response = self.supabase.table(self.table_name).update(data).eq("id", record_id).eq("user_id", user_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error updating {self.table_name} {record_id}: {e}")
            return False
    
    def delete(self, record_id: str, user_id: str) -> bool:
        """Delete a record."""
        try:
            response = self.supabase.table(self.table_name).delete().eq("id", record_id).eq("user_id", user_id).execute()
            return response.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting {self.table_name} {record_id}: {e}")
            return False 