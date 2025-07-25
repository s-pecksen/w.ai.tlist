from typing import List, Dict, Any, Optional
from src.models.slot import Slot, db
import logging

logger = logging.getLogger(__name__)

class SlotRepository:
    """Repository for slot-related database operations with PostgreSQL."""
    
    def get_available_slots(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all available slots for a user."""
        try:
            slots = Slot.query.filter_by(user_id=user_id, status='available').all()
            return [slot.to_dict() for slot in slots]
        except Exception as e:
            logger.error(f"Error getting available slots for user {user_id}: {e}")
            return []
    
    def get_by_status(self, user_id: str, status: str) -> List[Dict[str, Any]]:
        """Get slots by status."""
        try:
            slots = Slot.query.filter_by(user_id=user_id, status=status).all()
            return [slot.to_dict() for slot in slots]
        except Exception as e:
            logger.error(f"Error getting slots by status {status} for user {user_id}: {e}")
            return []
    
    def update_status(self, slot_id: str, user_id: str, status: str, proposed_patient_id: str = None, proposed_patient_name: str = None) -> bool:
        """Update slot status and proposed patient."""
        try:
            slot = Slot.query.filter_by(id=slot_id, user_id=user_id).first()
            if slot:
                slot.status = status
                if proposed_patient_id is not None:
                    slot.proposed_patient_id = proposed_patient_id
                if proposed_patient_name is not None:
                    slot.proposed_patient_name = proposed_patient_name
                db.session.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating slot status {slot_id}: {e}")
            db.session.rollback()
        return False
    
    def get_by_provider(self, user_id: str, provider_id: str) -> List[Dict[str, Any]]:
        """Get slots by provider."""
        try:
            slots = Slot.query.filter_by(user_id=user_id, provider_id=provider_id).all()
            return [slot.to_dict() for slot in slots]
        except Exception as e:
            logger.error(f"Error getting slots by provider {provider_id} for user {user_id}: {e}")
            return []
    
    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new slot."""
        try:
            slot = Slot.from_dict(data)
            db.session.add(slot)
            db.session.commit()
            return slot.to_dict()
        except Exception as e:
            logger.error(f"Error creating slot: {e}")
            db.session.rollback()
            return None
    
    def update(self, record_id: str, user_id: str, data: Dict[str, Any]) -> bool:
        """Update a slot."""
        try:
            slot = Slot.query.filter_by(id=record_id, user_id=user_id).first()
            if slot:
                for key, value in data.items():
                    if hasattr(slot, key):
                        # Handle date conversion for PostgreSQL
                        if key == 'date' and isinstance(value, str):
                            from datetime import datetime
                            value = datetime.strptime(value, '%Y-%m-%d').date()
                        # Handle duration conversion to integer
                        elif key == 'duration' and isinstance(value, str):
                            value = int(value)
                        setattr(slot, key, value)
                db.session.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating slot {record_id}: {e}")
            db.session.rollback()
        return False
    
    def delete(self, record_id: str, user_id: str) -> bool:
        """Delete a slot."""
        try:
            slot = Slot.query.filter_by(id=record_id, user_id=user_id).first()
            if slot:
                db.session.delete(slot)
                db.session.commit()
                return True
        except Exception as e:
            logger.error(f"Error deleting slot {record_id}: {e}")
            db.session.rollback()
        return False
    
    def get_by_id(self, slot_id: str) -> Optional[Dict[str, Any]]:
        """Get slot by ID."""
        try:
            slot = db.session.get(Slot, slot_id)
            return slot.to_dict() if slot else None
        except Exception as e:
            logger.error(f"Error getting slot {slot_id}: {e}")
            return None
    
    def get_all_slots(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all slots for a user."""
        try:
            slots = Slot.query.filter_by(user_id=user_id).all()
            return [slot.to_dict() for slot in slots]
        except Exception as e:
            logger.error(f"Error getting all slots for user {user_id}: {e}")
            return [] 