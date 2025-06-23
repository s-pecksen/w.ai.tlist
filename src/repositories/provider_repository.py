from typing import List, Dict, Any, Optional
from src.repositories.base_repository import BaseRepository
from src.database import get_supabase_client
from src.database_factory import DatabaseFactory
import logging

logger = logging.getLogger(__name__)

class ProviderRepository(BaseRepository):
    """Repository for provider-related database operations."""
    
    def __init__(self, app=None):
        super().__init__("providers")
        self.database = DatabaseFactory.get_database(app)
    
    def get_providers(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all providers for a user."""
        return self.database.get_providers(user_id)
    
    def get_provider_names(self, user_id: str) -> List[str]:
        """Get provider names as a list."""
        providers = self.get_providers(user_id)
        return [f"{p['first_name']} {p['last_initial'] or ''}".strip() for p in providers]
    
    def get_provider_map(self, user_id: str) -> Dict[str, str]:
        """Get a mapping of provider IDs to names."""
        providers = self.get_providers(user_id)
        return {str(p['id']): f"{p['first_name']} {p['last_initial'] or ''}".strip() for p in providers}
    
    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new provider."""
        return self.database.create_provider(data)
    
    def delete(self, record_id: str, user_id: str) -> bool:
        """Delete a provider."""
        return self.database.delete_provider(record_id, user_id) 