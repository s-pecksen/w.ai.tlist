from typing import List, Dict, Any, Tuple
from src.repositories.patient_repository import PatientRepository
from src.repositories.slot_repository import SlotRepository
from src.repositories.provider_repository import ProviderRepository
from src.utils.helpers import wait_time_to_days, wait_time_to_minutes
import logging
from datetime import datetime, time, timedelta

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
            slot = self.slot_repo.get_by_id(slot_id)
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
            logger.info(f"\n\n\nFINDING MATCHES FOR PATIENT {patient_id}\n\n\n")
            # Get the patient details
            patient = self.patient_repo.get_by_id(patient_id, user_id)
            if not patient:
                return []

            # Get all available slots
            slots = self.slot_repo.get_available_slots(user_id)
            
            # Log patient info for debugging
            logger.info(f"[MATCHING] Patient {patient.get('name')} ({patient_id}) availability: {patient.get('availability')}")
            logger.info(f"[MATCHING] Patient duration requirement: {patient.get('duration')} min")
            logger.info(f"[MATCHING] Patient preferred provider: {patient.get('provider', 'no preference')}")
            logger.info(f"[MATCHING] Found {len(slots)} total available slots")

            matching_slots = []
            
            # Use the same logic as find_matches_for_slot but in reverse
            for slot in slots:
                logger.info(f"[DEBUG] Checking slot: {slot.get('date')} {slot.get('start_time')} ({slot.get('duration')} min) with {slot.get('provider', 'Unknown Provider')}")
                
                # Use the unified compatibility checking method
                if self._is_slot_suitable_for_patient(slot, patient):
                    logger.info(f"[MATCH] Slot {slot.get('date')} {slot.get('start_time')} matches patient requirements")
                    
                    # Add provider_name for frontend compatibility
                    slot_copy = slot.copy()
                    slot_copy['provider_name'] = slot.get('provider', 'Unknown Provider')
                    matching_slots.append(slot_copy)
                else:
                    logger.info(f"[NO MATCH] Slot {slot.get('date')} {slot.get('start_time')} does not match patient requirements")

            # Sort by date and time, handling missing 'start_time' fields gracefully
            matching_slots.sort(key=lambda s: (s.get('date', ''), s.get('start_time', '')))
            
            logger.info(f"[MATCHING] Found {len(matching_slots)} matching slots for patient {patient.get('name')}")
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
        
        # Check availability and duration using the same logic as find_matches_for_patient
        if not self._check_comprehensive_compatibility(patient, slot):
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
        
        # Check availability and duration using the same logic as find_matches_for_patient
        if not self._check_comprehensive_compatibility(patient, slot):
            return False
        
        return True
    
    def _check_comprehensive_compatibility(self, patient: Dict[str, Any], slot: Dict[str, Any]) -> bool:
        """Check if patient availability and duration are compatible with slot using the same logic as find_matches_for_patient."""
        patient_availability = patient.get('availability', {})
        slot_date = slot.get('date')
        slot_start_time = slot.get('start_time')
        slot_duration = slot.get('duration', 0)
        desired_duration = int(patient.get('duration', 0))
        
        if not slot_date or not slot_start_time:
            return True
        
        # Check duration compatibility first
        if slot_duration < desired_duration:
            return False
        
        # Convert date to day name
        try:
            slot_datetime = datetime.strptime(slot_date, '%Y-%m-%d')
            slot_day_name = slot_datetime.strftime('%A')  # Monday, Tuesday, etc.
        except:
            return True
        
        # Parse slot start time
        try:
            slot_start_time_obj = datetime.strptime(slot_start_time, '%H:%M').time()
        except:
            return True
        
        # Calculate slot end time from start time and duration
        if slot_start_time_obj and slot_duration:
            start_dt = datetime.combine(datetime.today(), slot_start_time_obj)
            end_dt = start_dt + timedelta(minutes=slot_duration)
            slot_end_time_obj = end_dt.time()
        else:
            return True
        
        # If patient has no availability restrictions (flexible), they match any slot
        if not patient_availability:
            return True
        
        # Check if patient has availability on this day
        if slot_day_name not in patient_availability:
            return False
        
        # Check overlap with patient's availability periods
        am_range = (time(0, 0, 0), time(11, 59, 59))
        pm_range = (time(12, 0, 0), time(23, 59, 59))
        
        patient_periods = patient_availability[slot_day_name]
        for period in patient_periods:
            if period == 'AM':
                avail_start, avail_end = am_range
            elif period == 'PM':
                avail_start, avail_end = pm_range
            else:
                continue
            
            # Check if slot time overlaps with patient availability
            if slot_start_time_obj < avail_end and slot_end_time_obj > avail_start:
                return True
        
        return False
    
    def _check_availability_compatibility(self, patient: Dict[str, Any], slot: Dict[str, Any]) -> bool:
        """Check if patient availability is compatible with slot."""
        # Use the comprehensive compatibility check for consistency
        return self._check_comprehensive_compatibility(patient, slot)
    
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