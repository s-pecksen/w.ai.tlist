from typing import List, Dict, Any, Tuple
from src.repositories.patient_repository import PatientRepository
from src.repositories.slot_repository import SlotRepository
from src.repositories.provider_repository import ProviderRepository
from src.utils.helpers import wait_time_to_days, wait_time_to_minutes
import logging

logger = logging.getLogger(__name__)

class MatchingService:
    """Service for handling patient-slot matching logic."""
    
    def __init__(self):
        self.patient_repo = PatientRepository()
        self.slot_repo = SlotRepository()
        self.provider_repo = ProviderRepository()
    
    def find_matches_for_slot(self, slot_id: str, user_id: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Find eligible and ineligible patients for a specific slot."""
        try:
            # Get the slot details
            slot = self.slot_repo.get_by_id(slot_id, user_id)
            if not slot:
                return [], []
            
            # Get all waiting patients
            patients = self.patient_repo.get_by_status(user_id, "waiting")
            
            eligible_patients = []
            ineligible_patients = []
            
            for patient in patients:
                if self._is_patient_eligible_for_slot(patient, slot):
                    eligible_patients.append(patient)
                else:
                    ineligible_patients.append(patient)
            
            # Sort eligible patients by priority
            eligible_patients.sort(key=lambda p: self._get_eligible_sort_key(p))
            
            # Sort ineligible patients by wait time
            ineligible_patients.sort(key=lambda p: self._get_waitlist_sort_key(p))
            
            return eligible_patients, ineligible_patients
            
        except Exception as e:
            logger.error(f"Error finding matches for slot {slot_id}: {e}")
            return [], []
    
    def find_matches_for_patient(self, patient_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Find available slots for a specific patient."""
        try:
            # Get the patient details
            patient = self.patient_repo.get_by_id(patient_id, user_id)
            if not patient:
                return []
            
            # Get all available slots
            slots = self.slot_repo.get_available_slots(user_id)
            
            # Filter slots based on patient requirements
            matching_slots = []
            for slot in slots:
                if self._is_slot_suitable_for_patient(slot, patient):
                    matching_slots.append(slot)
            
            # Sort by date and time
            matching_slots.sort(key=lambda s: (s['date'], s['time']))
            
            return matching_slots
            
        except Exception as e:
            logger.error(f"Error finding matches for patient {patient_id}: {e}")
            return []
    
    def _is_patient_eligible_for_slot(self, patient: Dict[str, Any], slot: Dict[str, Any]) -> bool:
        """Check if a patient is eligible for a specific slot."""
        # Check provider preference
        if patient.get('provider') and patient['provider'] != 'no preference':
            if str(slot.get('provider')) != patient['provider']:
                return False
        
        # Check appointment type compatibility
        if patient.get('appointment_type') and slot.get('appointment_type'):
            if patient['appointment_type'] != slot['appointment_type']:
                return False
        
        # Check availability
        if not self._check_availability_compatibility(patient, slot):
            return False
        
        return True
    
    def _is_slot_suitable_for_patient(self, slot: Dict[str, Any], patient: Dict[str, Any]) -> bool:
        """Check if a slot is suitable for a specific patient."""
        # Check provider preference
        if patient.get('provider') and patient['provider'] != 'no preference':
            if str(slot.get('provider')) != patient['provider']:
                return False
        
        # Check appointment type compatibility
        if patient.get('appointment_type') and slot.get('appointment_type'):
            if patient['appointment_type'] != slot['appointment_type']:
                return False
        
        # Check availability
        if not self._check_availability_compatibility(patient, slot):
            return False
        
        return True
    
    def _check_availability_compatibility(self, patient: Dict[str, Any], slot: Dict[str, Any]) -> bool:
        """Check if patient availability is compatible with slot."""
        patient_availability = patient.get('availability', {})
        if not patient_availability:
            return True  # No restrictions
        
        # Get slot day and period
        slot_date = slot.get('date')
        slot_period = slot.get('slot_period')
        
        if not slot_date or not slot_period:
            return True
        
        # Convert date to day name
        from datetime import datetime
        try:
            slot_datetime = datetime.strptime(slot_date, '%Y-%m-%d')
            day_name = slot_datetime.strftime('%A')  # Monday, Tuesday, etc.
        except:
            return True
        
        # Check if patient is available on this day and period
        if day_name in patient_availability:
            return slot_period in patient_availability[day_name]
        
        return False
    
    def _get_eligible_sort_key(self, patient: Dict[str, Any]) -> Tuple[int, int, int]:
        """Get sort key for eligible patients (urgency, wait time, name)."""
        urgency_order = {'high': 0, 'medium': 1, 'low': 2}
        urgency = urgency_order.get(patient.get('urgency', 'medium'), 1)
        wait_days = wait_time_to_days(patient.get('wait_time', '0 days'))
        name = patient.get('name', '').lower()
        return (urgency, -wait_days, name)
    
    def _get_waitlist_sort_key(self, patient: Dict[str, Any]) -> Tuple[int, str]:
        """Get sort key for waitlist patients (wait time, name)."""
        wait_days = wait_time_to_days(patient.get('wait_time', '0 days'))
        name = patient.get('name', '').lower()
        return (-wait_days, name) 