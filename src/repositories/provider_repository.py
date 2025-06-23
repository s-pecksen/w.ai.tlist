from typing import List, Dict, Any, Optional
from src.models.provider import Provider, db
import logging

logger = logging.getLogger(__name__)

class ProviderRepository:
    """Repository for provider-related database operations with SQLite."""
    
    def get_providers(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all providers for a user."""
        try:
            providers = Provider.query.filter_by(user_id=user_id).all()
            return [provider.to_dict() for provider in providers]
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
    
    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new provider."""
        try:
            provider = Provider.from_dict(data)
            db.session.add(provider)
            db.session.commit()
            return provider.to_dict()
        except Exception as e:
            logger.error(f"Error creating provider: {e}")
            db.session.rollback()
            return None
    
    def delete(self, record_id: str, user_id: str) -> bool:
        """Delete a provider."""
        try:
            provider = Provider.query.filter_by(id=record_id, user_id=user_id).first()
            if provider:
                db.session.delete(provider)
                db.session.commit()
                return True
        except Exception as e:
            logger.error(f"Error deleting provider {record_id}: {e}")
            db.session.rollback()
        return False
    
    def get_by_id(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Get provider by ID."""
        try:
            provider = Provider.query.get(provider_id)
            return provider.to_dict() if provider else None
        except Exception as e:
            logger.error(f"Error getting provider {provider_id}: {e}")
            return None
    
    def update(self, provider_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a provider."""
        try:
            provider = Provider.query.get(provider_id)
            if provider:
                for key, value in data.items():
                    if hasattr(provider, key):
                        setattr(provider, key, value)
                db.session.commit()
                return provider.to_dict()
        except Exception as e:
            logger.error(f"Error updating provider {provider_id}: {e}")
            db.session.rollback()
        return None 