from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from src.config import Config
from src.database import get_supabase_client
from src.models.provider import db, Provider
from src.models.patient import Patient
from src.models.slot import Slot
import logging

logger = logging.getLogger(__name__)

class DatabaseInterface(ABC):
    """Abstract interface for database operations."""
    
    @abstractmethod
    def get_providers(self, user_id: str) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def create_provider(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def delete_provider(self, provider_id: str, user_id: str) -> bool:
        pass
    
    @abstractmethod
    def get_patients(self, user_id: str) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def create_patient(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def update_patient(self, patient_id: str, user_id: str, data: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    def get_slots(self, user_id: str) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def create_slot(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def update_slot(self, slot_id: str, user_id: str, data: Dict[str, Any]) -> bool:
        pass

class SupabaseDatabase(DatabaseInterface):
    """Supabase database implementation."""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    def get_providers(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            response = self.supabase.table("providers").select("*").eq("user_id", user_id).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting providers from Supabase: {e}")
            return []
    
    def create_provider(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            response = self.supabase.table("providers").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating provider in Supabase: {e}")
            return None
    
    def delete_provider(self, provider_id: str, user_id: str) -> bool:
        try:
            response = self.supabase.table("providers").delete().eq("id", provider_id).eq("user_id", user_id).execute()
            return response.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting provider from Supabase: {e}")
            return False
    
    def get_patients(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            response = self.supabase.table("patients").select("*").eq("user_id", user_id).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting patients from Supabase: {e}")
            return []
    
    def create_patient(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            response = self.supabase.table("patients").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating patient in Supabase: {e}")
            return None
    
    def update_patient(self, patient_id: str, user_id: str, data: Dict[str, Any]) -> bool:
        try:
            response = self.supabase.table("patients").update(data).eq("id", patient_id).eq("user_id", user_id).execute()
            return response.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating patient in Supabase: {e}")
            return False
    
    def get_slots(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            response = self.supabase.table("cancelled_slots").select("*").eq("user_id", user_id).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting slots from Supabase: {e}")
            return []
    
    def create_slot(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            response = self.supabase.table("cancelled_slots").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating slot in Supabase: {e}")
            return None
    
    def update_slot(self, slot_id: str, user_id: str, data: Dict[str, Any]) -> bool:
        try:
            response = self.supabase.table("cancelled_slots").update(data).eq("id", slot_id).eq("user_id", user_id).execute()
            return response.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating slot in Supabase: {e}")
            return False

class LocalDatabase(DatabaseInterface):
    """Local SQLite database implementation."""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            db.init_app(app)
    
    def get_providers(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            providers = Provider.query.filter_by(user_id=user_id).all()
            return [provider.to_dict() for provider in providers]
        except Exception as e:
            logger.error(f"Error getting providers from local DB: {e}")
            return []
    
    def create_provider(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            provider = Provider.from_dict(data)
            db.session.add(provider)
            db.session.commit()
            return provider.to_dict()
        except Exception as e:
            logger.error(f"Error creating provider in local DB: {e}")
            db.session.rollback()
            return None
    
    def delete_provider(self, provider_id: str, user_id: str) -> bool:
        try:
            provider = Provider.query.filter_by(id=provider_id, user_id=user_id).first()
            if provider:
                db.session.delete(provider)
                db.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting provider from local DB: {e}")
            db.session.rollback()
            return False
    
    def get_patients(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            patients = Patient.query.filter_by(user_id=user_id).all()
            return [patient.to_dict() for patient in patients]
        except Exception as e:
            logger.error(f"Error getting patients from local DB: {e}")
            return []
    
    def create_patient(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            patient = Patient.from_dict(data)
            db.session.add(patient)
            db.session.commit()
            return patient.to_dict()
        except Exception as e:
            logger.error(f"Error creating patient in local DB: {e}")
            db.session.rollback()
            return None
    
    def update_patient(self, patient_id: str, user_id: str, data: Dict[str, Any]) -> bool:
        try:
            patient = Patient.query.filter_by(id=patient_id, user_id=user_id).first()
            if patient:
                for key, value in data.items():
                    if hasattr(patient, key):
                        setattr(patient, key, value)
                db.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating patient in local DB: {e}")
            db.session.rollback()
            return False
    
    def get_slots(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            slots = Slot.query.filter_by(user_id=user_id).all()
            return [slot.to_dict() for slot in slots]
        except Exception as e:
            logger.error(f"Error getting slots from local DB: {e}")
            return []
    
    def create_slot(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            slot = Slot.from_dict(data)
            db.session.add(slot)
            db.session.commit()
            return slot.to_dict()
        except Exception as e:
            logger.error(f"Error creating slot in local DB: {e}")
            db.session.rollback()
            return None
    
    def update_slot(self, slot_id: str, user_id: str, data: Dict[str, Any]) -> bool:
        try:
            slot = Slot.query.filter_by(id=slot_id, user_id=user_id).first()
            if slot:
                for key, value in data.items():
                    if hasattr(slot, key):
                        setattr(slot, key, value)
                db.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating slot in local DB: {e}")
            db.session.rollback()
            return False

class DatabaseFactory:
    """Factory to create appropriate database instance."""
    
    @staticmethod
    def get_database(app=None) -> DatabaseInterface:
        if Config.USE_LOCAL_DB:
            logger.info("Using local SQLite database")
            return LocalDatabase(app)
        else:
            logger.info("Using Supabase database")
            return SupabaseDatabase() 