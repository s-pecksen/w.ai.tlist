from typing import List, Dict, Any, Optional
from src.models.patient import Patient, db
import logging

logger = logging.getLogger(__name__)

class PatientRepository:
    """Repository for patient-related database operations with SQLite."""
    
    def get_waitlist(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all patients in the waitlist for a user."""
        try:
            patients = Patient.query.filter_by(user_id=user_id).all()
            return [patient.to_dict() for patient in patients]
        except Exception as e:
            logger.error(f"Error getting patients for user {user_id}: {e}")
            return []
    
    def get_by_status(self, user_id: str, status: str) -> List[Dict[str, Any]]:
        """Get patients by status."""
        try:
            patients = Patient.query.filter_by(user_id=user_id, status=status).all()
            return [patient.to_dict() for patient in patients]
        except Exception as e:
            logger.error(f"Error getting patients by status {status} for user {user_id}: {e}")
            return []
    
    def update_status(self, patient_id: str, user_id: str, status: str, proposed_slot_id: str = None) -> bool:
        """Update patient status and proposed slot."""
        try:
            patient = Patient.query.filter_by(id=patient_id, user_id=user_id).first()
            if patient:
                patient.status = status
                if proposed_slot_id is not None:
                    patient.proposed_slot_id = proposed_slot_id
                db.session.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating patient status {patient_id}: {e}")
            db.session.rollback()
        return False
    
    def bulk_create(self, patients_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create multiple patients at once."""
        try:
            created_patients = []
            for patient_data in patients_data:
                patient = Patient.from_dict(patient_data)
                db.session.add(patient)
                created_patients.append(patient)
            db.session.commit()
            return [patient.to_dict() for patient in created_patients]
        except Exception as e:
            logger.error(f"Error bulk creating patients: {e}")
            db.session.rollback()
            return []
    
    def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new patient."""
        try:
            patient = Patient.from_dict(data)
            db.session.add(patient)
            db.session.commit()
            return patient.to_dict()
        except Exception as e:
            logger.error(f"Error creating patient: {e}")
            db.session.rollback()
            return None
    
    def update(self, record_id: str, user_id: str, data: Dict[str, Any]) -> bool:
        """Update a patient."""
        try:
            patient = Patient.query.filter_by(id=record_id, user_id=user_id).first()
            if patient:
                for key, value in data.items():
                    if hasattr(patient, key):
                        setattr(patient, key, value)
                db.session.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating patient {record_id}: {e}")
            db.session.rollback()
        return False
    
    def delete(self, record_id: str, user_id: str) -> bool:
        """Delete a patient."""
        try:
            patient = Patient.query.filter_by(id=record_id, user_id=user_id).first()
            if patient:
                db.session.delete(patient)
                db.session.commit()
                return True
        except Exception as e:
            logger.error(f"Error deleting patient {record_id}: {e}")
            db.session.rollback()
        return False
    
    def get_by_id(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get patient by ID."""
        try:
            patient = Patient.query.get(patient_id)
            return patient.to_dict() if patient else None
        except Exception as e:
            logger.error(f"Error getting patient {patient_id}: {e}")
            return None 