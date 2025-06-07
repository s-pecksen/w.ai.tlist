from datetime import datetime, timedelta
import logging
import uuid
import json
from typing import List, Dict, Any, Optional
from .database import db, Provider, Patient, CancelledSlot
from cryptography.fernet import Fernet
from sqlalchemy.types import TypeDecorator, String
import os

class EncryptedString(TypeDecorator):
    impl = String
    
    def __init__(self, key=None):
        super().__init__()
        self.key = key or os.environ.get("FLASK_APP_ENCRYPTION_KEY")
        self.cipher_suite = Fernet(self.key.encode())
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            return self.cipher_suite.encrypt(value.encode()).decode()
        return value
    
    def process_result_value(self, value, dialect):
        if value is not None:
            return self.cipher_suite.decrypt(value.encode()).decode()
        return value

class DBProviderManager:
    """Manages providers using the database."""

    def __init__(self, user_id: str):
        """Initialize with user ID."""
        self.user_id = user_id

    def get_provider_list(self) -> List[Dict[str, Any]]:
        """Get all providers for the current user."""
        providers = Provider.query.filter_by(user_id=self.user_id).all()
        return [p.to_dict() for p in providers]

    def add_provider(self, first_name: str, last_initial: Optional[str] = None) -> bool:
        """Add a new provider."""
        try:
            # Check if provider already exists
            existing = Provider.query.filter_by(
                user_id=self.user_id,
                first_name=first_name,
                last_initial=last_initial
            ).first()
            
            if existing:
                return False
                
            provider = Provider(
                first_name=first_name,
                last_initial=last_initial,
                user_id=self.user_id
            )
            db.session.add(provider)
            db.session.commit()
            return True
        except Exception as e:
            logging.error(f"Error adding provider: {e}", exc_info=True)
            db.session.rollback()
            return False

    def remove_provider(self, first_name: str, last_initial: Optional[str] = None) -> bool:
        """Remove a provider."""
        try:
            provider = Provider.query.filter_by(
                user_id=self.user_id,
                first_name=first_name,
                last_initial=last_initial
            ).first()
            
            if provider:
                db.session.delete(provider)
                db.session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"Error removing provider: {e}", exc_info=True)
            db.session.rollback()
            return False

class DBPatientWaitlistManager:
    """Manages the patient waitlist using the database."""

    def __init__(self, user_id: str):
        """Initialize with user ID."""
        self.user_id = user_id

    def get_all_patients(self) -> List[Dict[str, Any]]:
        """Get all patients for the current user."""
        patients = Patient.query.filter_by(user_id=self.user_id).all()
        return [p.to_dict() for p in patients]

    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific patient by ID."""
        patient = Patient.query.filter_by(id=patient_id, user_id=self.user_id).first()
        return patient.to_dict() if patient else None

    def add_patient(
        self,
        name: str,
        phone: str,
        email: str = "",
        reason: str = "",
        urgency: str = "medium",
        appointment_type: str = "",
        duration: int = 30,
        provider: str = "no preference",
        timestamp: Optional[datetime] = None,
        availability: Optional[Dict] = None,
        availability_mode: str = "available",
        **p_data
    ) -> bool:
        """Add a new patient to the waitlist."""
        try:
            patient = Patient(
                id=str(uuid.uuid4()),
                name=name,
                phone=phone,
                email=email,
                reason=reason,
                urgency=urgency,
                appointment_type=appointment_type,
                duration=duration,
                provider=provider,
                timestamp=timestamp or datetime.utcnow(),
                availability=json.dumps(availability) if availability else None,
                availability_mode=availability_mode,
                user_id=self.user_id
            )
            db.session.add(patient)
            db.session.commit()
            return True
        except Exception as e:
            logging.error(f"Error adding patient: {e}", exc_info=True)
            db.session.rollback()
            return False

    def remove_patient(self, patient_id: str) -> bool:
        """Remove a patient from the waitlist."""
        try:
            patient = Patient.query.filter_by(id=patient_id, user_id=self.user_id).first()
            if patient:
                db.session.delete(patient)
                db.session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"Error removing patient: {e}", exc_info=True)
            db.session.rollback()
            return False

    def update_patient(
        self,
        patient_id: str,
        name: str,
        phone: str,
        email: str = "",
        reason: str = "",
        urgency: str = "medium",
        appointment_type: str = "",
        duration: int = 30,
        provider: str = "no preference",
        availability: Optional[Dict] = None,
        availability_mode: str = "available",
    ) -> bool:
        """Update a patient's information."""
        try:
            patient = Patient.query.filter_by(id=patient_id, user_id=self.user_id).first()
            if not patient:
                return False
                
            patient.name = name
            patient.phone = phone
            patient.email = email
            patient.reason = reason
            patient.urgency = urgency
            patient.appointment_type = appointment_type
            patient.duration = duration
            patient.provider = provider
            patient.availability = json.dumps(availability) if availability else None
            patient.availability_mode = availability_mode
            
            db.session.commit()
            return True
        except Exception as e:
            logging.error(f"Error updating patient: {e}", exc_info=True)
            db.session.rollback()
            return False

    def mark_as_pending(self, patient_id: str, slot_id: str) -> bool:
        """Mark a patient as pending for a specific slot."""
        try:
            patient = Patient.query.filter_by(id=patient_id, user_id=self.user_id).first()
            if not patient or patient.status != "waiting":
                return False
                
            patient.status = "pending"
            patient.proposed_slot_id = slot_id
            db.session.commit()
            return True
        except Exception as e:
            logging.error(f"Error marking patient as pending: {e}", exc_info=True)
            db.session.rollback()
            return False

    def cancel_proposal(self, patient_id: str) -> bool:
        """Reset a pending patient back to waiting."""
        try:
            patient = Patient.query.filter_by(id=patient_id, user_id=self.user_id).first()
            if not patient or patient.status != "pending":
                return False
                
            patient.status = "waiting"
            patient.proposed_slot_id = None
            db.session.commit()
            return True
        except Exception as e:
            logging.error(f"Error cancelling patient proposal: {e}", exc_info=True)
            db.session.rollback()
            return False

    def update_wait_times(self) -> None:
        """Update wait times for all waiting patients."""
        try:
            patients = Patient.query.filter_by(user_id=self.user_id).all()
            now = datetime.utcnow()
            
            for patient in patients:
                if patient.status == "waiting" and patient.timestamp:
                    wait_delta = now - patient.timestamp
                    days = wait_delta.days
                    patient.wait_time = f"{days} days"
            
            db.session.commit()
        except Exception as e:
            logging.error(f"Error updating wait times: {e}", exc_info=True)
            db.session.rollback()

class DBCancelledSlotManager:
    """Manages cancelled appointment slots using the database."""

    def __init__(self, user_id: str):
        """Initialize with user ID."""
        self.user_id = user_id

    def get_all_slots(self) -> List[Dict[str, Any]]:
        """Get all slots for the current user."""
        slots = CancelledSlot.query.filter_by(user_id=self.user_id).all()
        return [s.to_dict() for s in slots]

    def add_slot(
        self,
        provider: str,
        slot_date: str,
        slot_time: str,
        slot_period: str,
        duration: int,
        notes: str = ""
    ) -> bool:
        """Add a new cancelled appointment slot."""
        try:
            # Convert date string to datetime.date object
            try:
                date_obj = datetime.strptime(slot_date, "%Y-%m-%d").date()
            except ValueError:
                logging.error(f"Invalid date format: {slot_date}")
                return False

            slot = CancelledSlot(
                id=str(uuid.uuid4()),
                provider=provider,
                duration=duration,
                slot_date=date_obj,
                slot_period=slot_period,
                slot_time=slot_time,
                notes=notes,
                status="available",
                user_id=self.user_id
            )
            db.session.add(slot)
            db.session.commit()
            return True
        except Exception as e:
            logging.error(f"Error adding slot: {e}", exc_info=True)
            db.session.rollback()
            return False

    def remove_slot(self, slot_id: str) -> bool:
        """Remove a cancelled appointment slot."""
        try:
            slot = CancelledSlot.query.filter_by(id=slot_id, user_id=self.user_id).first()
            if slot:
                db.session.delete(slot)
                db.session.commit()
                return True
            return False
        except Exception as e:
            logging.error(f"Error removing slot: {e}", exc_info=True)
            db.session.rollback()
            return False

    def update_slot(
        self,
        slot_id: str,
        provider: str,
        slot_date: str,
        slot_time: str,
        slot_period: str,
        duration: int,
        notes: str = ""
    ) -> bool:
        """Update an existing cancelled appointment slot."""
        try:
            slot = CancelledSlot.query.filter_by(id=slot_id, user_id=self.user_id).first()
            if not slot:
                return False

            try:
                date_obj = datetime.strptime(slot_date, "%Y-%m-%d").date()
            except ValueError:
                logging.error(f"Invalid date format: {slot_date}")
                return False

            slot.provider = provider
            slot.duration = duration
            slot.slot_date = date_obj
            slot.slot_period = slot_period
            slot.slot_time = slot_time
            slot.notes = notes
            slot.status = "available"
            slot.proposed_patient_id = None
            slot.proposed_patient_name = None
            
            db.session.commit()
            return True
        except Exception as e:
            logging.error(f"Error updating slot: {e}", exc_info=True)
            db.session.rollback()
            return False

    def mark_as_pending(self, slot_id: str, patient_id: str, patient_name: str = "Unknown") -> bool:
        """Mark a slot as pending for a specific patient."""
        try:
            slot = CancelledSlot.query.filter_by(id=slot_id, user_id=self.user_id).first()
            if not slot or slot.status != "available":
                return False
                
            slot.status = "pending"
            slot.proposed_patient_id = patient_id
            slot.proposed_patient_name = patient_name
            db.session.commit()
            return True
        except Exception as e:
            logging.error(f"Error marking slot as pending: {e}", exc_info=True)
            db.session.rollback()
            return False

    def cancel_proposal(self, slot_id: str) -> bool:
        """Reset a pending slot back to available."""
        try:
            slot = CancelledSlot.query.filter_by(id=slot_id, user_id=self.user_id).first()
            if not slot or slot.status != "pending":
                return False
                
            slot.status = "available"
            slot.proposed_patient_id = None
            slot.proposed_patient_name = None
            db.session.commit()
            return True
        except Exception as e:
            logging.error(f"Error cancelling slot proposal: {e}", exc_info=True)
            db.session.rollback()
            return False 