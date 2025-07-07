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

            # Log patient's availabilities
            # logger.info(f"[MATCHING] Patient {patient.get('name')} ({patient_id}) availability: {patient.get('availability')}")

            # Get all available slots
            slots = self.slot_repo.get_available_slots(user_id)

            # Debug: Print each open slot's day/time and the patient's availabilities
            logger.info("\n\n ALL SLOTS + PATIENT AVAILABILITIES (with times)\n\n")
            # Print open slots with start times
            slot_structs = []
            for slot in slots:
                slot_day = slot.get('date')
                slot_start = slot.get('start_time')
                slot_duration = slot.get('duration', 0)
                logger.info(f"[DEBUG] Open slot: {slot_day} {slot_start} ({slot_duration} min)")
                slot_structs.append({'date': slot_day, 'start': slot_start, 'duration': slot_duration, 'slot': slot})

            # Print patient availabilities with time ranges
            patient_avail = patient.get('availability', {})
            am_range = (time(0, 0, 0), time(11, 59, 59))
            pm_range = (time(12, 0, 0), time(23, 59, 59))
            patient_structs = []
            for day, periods in patient_avail.items():
                for period in periods:
                    if period == 'AM':
                        logger.info(f"[DEBUG] Patient available: {day} AM (00:00 to 11:59)")
                        patient_structs.append({'day': day, 'range': am_range, 'period': 'AM'})
                    elif period == 'PM':
                        logger.info(f"[DEBUG] Patient available: {day} PM (12:00 to 23:59)")
                        patient_structs.append({'day': day, 'range': pm_range, 'period': 'PM'})
            logger.info(f"[DEBUG] Patient desired appointment duration: {patient.get('duration')}")

            # Log patient's preferred provider (name)
            preferred_provider_name = patient.get('provider', 'no preference')
            if preferred_provider_name == 'no preference':
                preferred_provider_name = 'No preference'
            logger.info(f"[DEBUG] Patient preferred provider: {preferred_provider_name}")

            # Find and log all potential matches
            logger.info("[DEBUG] Potential matches:")
            desired_duration = int(patient.get('duration', 0))
            matching_slots = []
            for slot_struct in slot_structs:
                slot_day = slot_struct['date']
                slot_start = slot_struct['start']
                slot_duration = slot_struct['duration']
                slot_obj = slot_struct['slot']
                # Provider is now stored as name directly, not UUID
                slot_provider_name = slot_obj.get('provider', 'Unknown Provider')
                # Parse slot start time
                try:
                    slot_start_time = datetime.strptime(slot_start, '%H:%M').time() if slot_start else None
                except Exception as e:
                    logger.info(f"[DEBUG] Could not parse slot start time: {slot_start}")
                    continue
                # Get day name
                try:
                    slot_day_name = datetime.strptime(slot_day, '%Y-%m-%d').strftime('%A')
                except Exception as e:
                    logger.info(f"[DEBUG] Could not parse slot date: {slot_day}")
                    continue
                # Calculate end time from start time and duration
                if slot_start_time and slot_duration:
                    start_dt = datetime.combine(datetime.today(), slot_start_time)
                    end_dt = start_dt + timedelta(minutes=slot_duration)
                    slot_end_time = end_dt.time()
                else:
                    slot_end_time = None
                
                # Check if patient has no availability restrictions (flexible)
                if not patient_structs:
                    # Patient is flexible - check duration and provider preference only
                    duration_ok = slot_duration >= desired_duration
                    
                    # Check provider preference match
                    provider_match = True
                    if preferred_provider_name != 'No preference':
                        provider_match = (slot_provider_name == preferred_provider_name)
                    
                    if duration_ok and provider_match:
                        logger.info(f"[MATCH] Slot {slot_day} {slot_start} ({slot_duration} min) with provider {slot_provider_name} matches flexible patient duration {desired_duration} min (Patient preferred provider: {preferred_provider_name})")
                        # Add provider_name for frontend
                        slot_copy = slot_obj.copy()
                        slot_copy['provider_name'] = slot_provider_name
                        matching_slots.append(slot_copy)
                else:
                    # Patient has specific availability - check overlap
                    for avail in patient_structs:
                        if avail['day'] == slot_day_name:
                            # Check overlap
                            avail_start, avail_end = avail['range']
                            if slot_start_time and slot_end_time:
                                overlap = (slot_start_time < avail_end and slot_end_time > avail_start)
                                duration_ok = slot_duration >= desired_duration
                                
                                # Check provider preference match
                                provider_match = True
                                if preferred_provider_name != 'No preference':
                                    provider_match = (slot_provider_name == preferred_provider_name)
                                
                                if overlap and duration_ok and provider_match:
                                    logger.info(f"[MATCH] Slot {slot_day} {slot_start} ({slot_duration} min) with provider {slot_provider_name} matches patient {avail['day']} {avail['period']} and duration {desired_duration} min (Patient preferred provider: {preferred_provider_name})")
                                    # Add provider_name for frontend
                                    slot_copy = slot_obj.copy()
                                    slot_copy['provider_name'] = slot_provider_name
                                    matching_slots.append(slot_copy)
                            break  # Only process first matching availability for this slot

            # Sort by date and time, handling missing 'start_time' fields gracefully
            matching_slots.sort(key=lambda s: (s.get('date', ''), s.get('start_time', '')))

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
        
        # Get slot day and start time
        slot_date = slot.get('date')
        slot_start_time = slot.get('start_time')
        
        if not slot_date or not slot_start_time:
            return True
        
        # Convert date to day name
        try:
            slot_datetime = datetime.strptime(slot_date, '%Y-%m-%d')
            day_name = slot_datetime.strftime('%A')  # Monday, Tuesday, etc.
        except:
            return True
        
        # Parse slot start time to determine AM/PM
        try:
            time_obj = datetime.strptime(slot_start_time, '%H:%M').time()
            slot_period = "PM" if time_obj.hour >= 12 else "AM"
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