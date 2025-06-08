from datetime import datetime, timedelta
import logging
import uuid
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from src.models import User, Provider, Patient, CancelledSlot

logger = logging.getLogger(__name__)


class DBProviderManager:
    """Manages providers using the database."""

    def __init__(self, user_id: str, db_session: AsyncSession):
        """Initialize with user ID and database session."""
        self.user_id = user_id
        self.db = db_session

    async def get_provider_list(self) -> List[Dict[str, Any]]:
        """Get all providers for the current user."""
        try:
            # Get user first
            result = await self.db.execute(
                select(User).where(User.username == self.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return []

            # Get providers for the user
            result = await self.db.execute(
                select(Provider).where(Provider.user_id == user.id)
            )
            providers = result.scalars().all()
            
            return [
                {
                    'id': p.id,
                    'name': f"{p.first_name} {p.last_initial}" if p.last_initial else p.first_name,
                    'first_name': p.first_name,
                    'last_initial': p.last_initial
                }
                for p in providers
            ]
        except Exception as e:
            logger.error(f"Error getting provider list: {e}", exc_info=True)
            return []

    async def add_provider(self, first_name: str, last_initial: Optional[str] = None) -> bool:
        """Add a new provider."""
        try:
            # Get user first
            result = await self.db.execute(
                select(User).where(User.username == self.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return False

            # Check if provider already exists
            result = await self.db.execute(
                select(Provider).where(
                    Provider.user_id == user.id,
                    Provider.first_name == first_name,
                    Provider.last_initial == (last_initial or "")
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                return False

            # Create full name
            full_name = f"{first_name} {last_initial}" if last_initial else first_name
                
            provider = Provider(
                user_id=user.id,
                first_name=first_name,
                last_initial=last_initial or "",
                name=full_name
            )
            self.db.add(provider)
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding provider: {e}", exc_info=True)
            await self.db.rollback()
            return False

    async def remove_provider(self, first_name: str, last_initial: Optional[str] = None) -> bool:
        """Remove a provider."""
        try:
            # Get user first
            result = await self.db.execute(
                select(User).where(User.username == self.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return False

            result = await self.db.execute(
                select(Provider).where(
                    Provider.user_id == user.id,
                    Provider.first_name == first_name,
                    Provider.last_initial == (last_initial or "")
                )
            )
            provider = result.scalar_one_or_none()
            
            if provider:
                await self.db.delete(provider)
                await self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing provider: {e}", exc_info=True)
            await self.db.rollback()
            return False


class DBPatientWaitlistManager:
    """Manages the patient waitlist using the database."""

    def __init__(self, user_id: str, db_session: AsyncSession):
        """Initialize with user ID and database session."""
        self.user_id = user_id
        self.db = db_session

    async def get_all_patients(self) -> List[Dict[str, Any]]:
        """Get all patients for the current user."""
        try:
            # Get user first
            result = await self.db.execute(
                select(User).where(User.username == self.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return []

            # Get patients for the user
            result = await self.db.execute(
                select(Patient).where(Patient.user_id == user.id)
            )
            patients = result.scalars().all()
            
            return [
                {
                    'id': str(p.id),
                    'name': p.name,
                    'phone': p.phone,
                    'email': p.email,
                    'reason': p.reason,
                    'urgency': p.urgency,
                    'appointment_type': p.appointment_type,
                    'duration': str(p.duration),
                    'provider': p.provider,
                    'status': p.status,
                    'timestamp': p.timestamp.isoformat() if p.timestamp else None,
                    'wait_time': p.wait_time,
                    'availability': p.availability or {},
                    'availability_mode': p.availability_mode,
                    'proposed_slot_id': p.proposed_slot_id
                }
                for p in patients
            ]
        except Exception as e:
            logger.error(f"Error getting patients: {e}", exc_info=True)
            return []

    async def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific patient by ID."""
        try:
            # Get user first
            result = await self.db.execute(
                select(User).where(User.username == self.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return None

            result = await self.db.execute(
                select(Patient).where(
                    Patient.id == int(patient_id),
                    Patient.user_id == user.id
                )
            )
            patient = result.scalar_one_or_none()
            
            if patient:
                return {
                    'id': str(patient.id),
                    'name': patient.name,
                    'phone': patient.phone,
                    'email': patient.email,
                    'reason': patient.reason,
                    'urgency': patient.urgency,
                    'appointment_type': patient.appointment_type,
                    'duration': str(patient.duration),
                    'provider': patient.provider,
                    'status': patient.status,
                    'timestamp': patient.timestamp.isoformat() if patient.timestamp else None,
                    'wait_time': patient.wait_time,
                    'availability': patient.availability or {},
                    'availability_mode': patient.availability_mode,
                    'proposed_slot_id': patient.proposed_slot_id
                }
            return None
        except Exception as e:
            logger.error(f"Error getting patient: {e}", exc_info=True)
            return None

    async def add_patient(
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
        **kwargs
    ) -> bool:
        """Add a new patient to the waitlist."""
        try:
            # Get user first
            result = await self.db.execute(
                select(User).where(User.username == self.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return False

            patient = Patient(
                user_id=user.id,
                name=name,
                phone=phone,
                email=email,
                reason=reason,
                urgency=urgency,
                appointment_type=appointment_type,
                duration=duration,
                provider=provider,
                timestamp=timestamp or datetime.utcnow(),
                availability=availability or {},
                availability_mode=availability_mode,
                wait_time="0 minutes"
            )
            self.db.add(patient)
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding patient: {e}", exc_info=True)
            await self.db.rollback()
            return False

    async def remove_patient(self, patient_id: str) -> bool:
        """Remove a patient from the waitlist."""
        try:
            # Get user first
            result = await self.db.execute(
                select(User).where(User.username == self.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return False

            result = await self.db.execute(
                select(Patient).where(
                    Patient.id == int(patient_id),
                    Patient.user_id == user.id
                )
            )
            patient = result.scalar_one_or_none()
            
            if patient:
                await self.db.delete(patient)
                await self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing patient: {e}", exc_info=True)
            await self.db.rollback()
            return False

    async def update_patient(
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
            # Get user first
            result = await self.db.execute(
                select(User).where(User.username == self.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return False

            result = await self.db.execute(
                select(Patient).where(
                    Patient.id == int(patient_id),
                    Patient.user_id == user.id
                )
            )
            patient = result.scalar_one_or_none()
            
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
            patient.availability = availability or {}
            patient.availability_mode = availability_mode
            
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating patient: {e}", exc_info=True)
            await self.db.rollback()
            return False

    async def mark_as_pending(self, patient_id: str, slot_id: str) -> bool:
        """Mark a patient as pending for a specific slot."""
        try:
            # Get user first
            result = await self.db.execute(
                select(User).where(User.username == self.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return False

            result = await self.db.execute(
                select(Patient).where(
                    Patient.id == int(patient_id),
                    Patient.user_id == user.id
                )
            )
            patient = result.scalar_one_or_none()
            
            if not patient or patient.status != "waiting":
                return False
                
            patient.status = "pending"
            patient.proposed_slot_id = slot_id
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking patient as pending: {e}", exc_info=True)
            await self.db.rollback()
            return False

    async def cancel_proposal(self, patient_id: str) -> bool:
        """Cancel a pending proposal and return patient to waiting status."""
        try:
            # Get user first
            result = await self.db.execute(
                select(User).where(User.username == self.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return False

            result = await self.db.execute(
                select(Patient).where(
                    Patient.id == int(patient_id),
                    Patient.user_id == user.id
                )
            )
            patient = result.scalar_one_or_none()
            
            if not patient or patient.status != "pending":
                return False
                
            patient.status = "waiting"
            patient.proposed_slot_id = None
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error cancelling proposal: {e}", exc_info=True)
            await self.db.rollback()
            return False

    async def update_wait_times(self) -> None:
        """Update wait times for all patients."""
        try:
            # Get user first
            result = await self.db.execute(
                select(User).where(User.username == self.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return

            result = await self.db.execute(
                select(Patient).where(Patient.user_id == user.id)
            )
            patients = result.scalars().all()
            
            now = datetime.utcnow()
            for patient in patients:
                if patient.timestamp:
                    wait_duration = now - patient.timestamp
                    days = wait_duration.days
                    hours, remainder = divmod(wait_duration.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)
                    
                    if days > 0:
                        patient.wait_time = f"{days} days"
                    elif hours > 0:
                        patient.wait_time = f"{hours} hours"
                    else:
                        patient.wait_time = f"{minutes} minutes"
            
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error updating wait times: {e}", exc_info=True)


class DBCancelledSlotManager:
    """Manages cancelled appointment slots using the database."""

    def __init__(self, user_id: str, db_session: AsyncSession):
        """Initialize with user ID and database session."""
        self.user_id = user_id
        self.db = db_session

    async def get_all_slots(self) -> List[Dict[str, Any]]:
        """Get all slots for the current user."""
        try:
            # Get user first
            result = await self.db.execute(
                select(User).where(User.username == self.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return []

            result = await self.db.execute(
                select(CancelledSlot).where(CancelledSlot.user_id == user.id)
            )
            slots = result.scalars().all()
            
            return [
                {
                    'id': slot.slot_id,
                    'provider': slot.provider,
                    'slot_date': slot.slot_date,
                    'slot_time': slot.slot_time,
                    'slot_period': slot.slot_period,
                    'duration': slot.duration,
                    'status': slot.status,
                    'proposed_patient_id': slot.proposed_patient_id,
                    'proposed_patient_name': slot.proposed_patient_name,
                    'notes': slot.notes
                }
                for slot in slots
            ]
        except Exception as e:
            logger.error(f"Error getting slots: {e}", exc_info=True)
            return []

    async def add_slot(
        self,
        provider: str,
        slot_date: str,
        slot_time: str,
        slot_period: str,
        duration: int,
        notes: str = ""
    ) -> bool:
        """Add a new cancelled slot."""
        try:
            # Get user first
            result = await self.db.execute(
                select(User).where(User.username == self.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return False

            slot = CancelledSlot(
                user_id=user.id,
                slot_id=str(uuid.uuid4()),
                provider=provider,
                slot_date=slot_date,
                slot_time=slot_time,
                slot_period=slot_period,
                duration=duration,
                notes=notes,
                status="available"
            )
            self.db.add(slot)
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding slot: {e}", exc_info=True)
            await self.db.rollback()
            return False

    async def remove_slot(self, slot_id: str) -> bool:
        """Remove a slot."""
        try:
            # Get user first
            result = await self.db.execute(
                select(User).where(User.username == self.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return False

            result = await self.db.execute(
                select(CancelledSlot).where(
                    CancelledSlot.slot_id == slot_id,
                    CancelledSlot.user_id == user.id
                )
            )
            slot = result.scalar_one_or_none()
            
            if slot:
                await self.db.delete(slot)
                await self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing slot: {e}", exc_info=True)
            await self.db.rollback()
            return False

    async def update_slot(
        self,
        slot_id: str,
        provider: str,
        slot_date: str,
        slot_time: str,
        slot_period: str,
        duration: int,
        notes: str = ""
    ) -> bool:
        """Update a slot."""
        try:
            # Get user first
            result = await self.db.execute(
                select(User).where(User.username == self.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return False

            result = await self.db.execute(
                select(CancelledSlot).where(
                    CancelledSlot.slot_id == slot_id,
                    CancelledSlot.user_id == user.id
                )
            )
            slot = result.scalar_one_or_none()
            
            if not slot:
                return False
                
            slot.provider = provider
            slot.slot_date = slot_date
            slot.slot_time = slot_time
            slot.slot_period = slot_period
            slot.duration = duration
            slot.notes = notes
            
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating slot: {e}", exc_info=True)
            await self.db.rollback()
            return False

    async def mark_as_pending(self, slot_id: str, patient_id: str, patient_name: str = "Unknown") -> bool:
        """Mark a slot as pending for a specific patient."""
        try:
            # Get user first
            result = await self.db.execute(
                select(User).where(User.username == self.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return False

            result = await self.db.execute(
                select(CancelledSlot).where(
                    CancelledSlot.slot_id == slot_id,
                    CancelledSlot.user_id == user.id
                )
            )
            slot = result.scalar_one_or_none()
            
            if not slot or slot.status != "available":
                return False
                
            slot.status = "pending"
            slot.proposed_patient_id = patient_id
            slot.proposed_patient_name = patient_name
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking slot as pending: {e}", exc_info=True)
            await self.db.rollback()
            return False

    async def cancel_proposal(self, slot_id: str) -> bool:
        """Cancel a pending proposal and return slot to available status."""
        try:
            # Get user first
            result = await self.db.execute(
                select(User).where(User.username == self.user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return False

            result = await self.db.execute(
                select(CancelledSlot).where(
                    CancelledSlot.slot_id == slot_id,
                    CancelledSlot.user_id == user.id
                )
            )
            slot = result.scalar_one_or_none()
            
            if not slot or slot.status != "pending":
                return False
                
            slot.status = "available"
            slot.proposed_patient_id = None
            slot.proposed_patient_name = None
            await self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error cancelling proposal: {e}", exc_info=True)
            await self.db.rollback()
            return False 