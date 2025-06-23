from typing import List, Dict, Any, Optional
from src.repositories.base_repository import BaseRepository
from src.database import get_supabase_client
import logging

logger = logging.getLogger(__name__)

class ProviderRepository(BaseRepository):
    """Repository for provider-related database operations."""
    
    def __init__(self):
        super().__init__("providers")
    
    def get_providers(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all providers for a user."""
        try:
            response = self.supabase.table(self.table_name).select("*").eq("user_id", user_id).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting providers for user {user_id}: {e}")
            return []
    
    def get_provider_names(self, user_id: str) -> List[str]:
        """Get provider names as a list."""
        providers = self.get_providers(user_id)
        return [f"{p['first_name']} {p['last_initial'] or ''}".strip() for p in providers]
    
    def get_provider_map(self, user_id: str) -> Dict[str, str]:
        """Get a mapping of provider IDs to names."""
        providers = self.get_providers(user_id)
        return {str(p['id']): f"{p['first_name']} {p['last_initial'] or ''}".strip() for p in providers} 