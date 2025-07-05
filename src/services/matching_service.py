from typing import List, Dict, Any, Tuple
from src.repositories.patient_repository import PatientRepository
from src.repositories.slot_repository import SlotRepository
from src.repositories.provider_repository import ProviderRepository
from src.utils.helpers import wait_time_to_days, wait_time_to_minutes
import logging
from datetime import datetime, time

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
            logger.info(f"\n\n\n\n\nFINDING MATCHES FOR PATIENT {patient_id}\n\n\n\n\n")
            # Get the patient details
            patient = self.patient_repo.get_by_id(patient_id, user_id)
            if not patient:
                return []

            # Log patient's availabilities
            # logger.info(f"[MATCHING] Patient {patient.get('name')} ({patient_id}) availability: {patient.get('availability')}")

            # Get all available slots
            slots = self.slot_repo.get_available_slots(user_id)

            # Get provider map for UUID<->name mapping
            provider_map = self.provider_repo.get_provider_map(user_id)
            provider_repo = self.provider_repo

            # Log all provider availabilities
            # provider_availabilities = {}
            # for slot in slots:
            #     provider_id = str(slot.get('provider'))
            #     provider = provider_repo.get_by_id(provider_id)
            #     if provider:
            #         provider_availabilities[provider_id] = provider.get('availability', None)
            # logger.info(f"[MATCHING] Provider availabilities: {provider_availabilities}")

            # Debug: Print each open slot's day/time and the patient's availabilities
            logger.info("\n\n\n\n ALL SLOTS + PATIENT AVAILABILITIES (with times)\n\n\n\n")
            # Print open slots with start and end times
            slot_structs = []
            for slot in slots:
                slot_day = slot.get('date')
                slot_start = slot.get('start_time') or slot.get('time')
                slot_end = slot.get('end_time')
                logger.info(f"[DEBUG] Open slot: {slot_day} {slot_start} - {slot_end}")
                slot_structs.append({'date': slot_day, 'start': slot_start, 'end': slot_end, 'slot': slot})

            # Print patient availabilities with time ranges
            patient_avail = patient.get('availability', {})
            am_range = (time(0, 0, 0), time(11, 59, 59))
            pm_range = (time(12, 0, 0), time(23, 59, 59))
            patient_structs = []
            for day, periods in patient_avail.items():
                for period in periods:
                    if period == 'AM':
                        logger.info(f"[DEBUG] Patient available: {day} AM (12:00:00am to 11:59:59am)")
                        patient_structs.append({'day': day, 'range': am_range, 'period': 'AM'})
                    elif period == 'PM':
                        logger.info(f"[DEBUG] Patient available: {day} PM (12:00:00pm to 11:59:59pm)")
                        patient_structs.append({'day': day, 'range': pm_range, 'period': 'PM'})
            logger.info(f"[DEBUG] Patient desired appointment duration: {patient.get('duration')}")

            # Log patient's preferred provider (name)
            preferred_provider_uuid = patient.get('provider')
            if preferred_provider_uuid == 'no preference':
                preferred_provider_name = 'No preference'
            else:
                preferred_provider_name = provider_map.get(str(preferred_provider_uuid), 'Unknown')
            logger.info(f"[DEBUG] Patient preferred provider: {preferred_provider_name}")

            # Find and log all potential matches
            logger.info("[DEBUG] Potential matches:")
            desired_duration = int(patient.get('duration', 0))
            matching_slots = []
            for slot_struct in slot_structs:
                slot_day = slot_struct['date']
                slot_start = slot_struct['start']
                slot_end = slot_struct['end']
                slot_obj = slot_struct['slot']
                slot_provider_uuid = str(slot_obj.get('provider'))
                slot_provider_name = provider_map.get(slot_provider_uuid, 'Unknown')
                # Parse slot times
                try:
                    slot_start_time = datetime.strptime(slot_start, '%H:%M').time() if slot_start else None
                    slot_end_time = datetime.strptime(slot_end, '%H:%M').time() if slot_end else None
                except Exception as e:
                    logger.info(f"[DEBUG] Could not parse slot times: {slot_start}, {slot_end}")
                    continue
                # Get day name
                try:
                    slot_day_name = datetime.strptime(slot_day, '%Y-%m-%d').strftime('%A')
                except Exception as e:
                    logger.info(f"[DEBUG] Could not parse slot date: {slot_day}")
                    continue
                slot_duration = None
                if slot_start_time and slot_end_time:
                    slot_duration = (datetime.combine(datetime.today(), slot_end_time) - datetime.combine(datetime.today(), slot_start_time)).seconds // 60
                for avail in patient_structs:
                    if avail['day'] == slot_day_name:
                        # Check overlap
                        avail_start, avail_end = avail['range']
                        if slot_start_time and slot_end_time:
                            overlap = (slot_start_time < avail_end and slot_end_time > avail_start)
                            duration_ok = slot_duration is not None and slot_duration >= desired_duration
                            if overlap and duration_ok:
                                logger.info(f"[MATCH] Slot {slot_day} {slot_start}-{slot_end} ({slot_duration} min) with provider {slot_provider_name} matches patient {avail['day']} {avail['period']} and duration {desired_duration} min (Patient preferred provider: {preferred_provider_name})")
                                # Add provider_name for frontend
                                slot_copy = slot_obj.copy()
                                slot_copy['provider_name'] = slot_provider_name
                                matching_slots.append(slot_copy)

            # Sort by date and time, handling missing 'time' fields gracefully
            matching_slots.sort(key=lambda s: (s['date'], s.get('time', '') or s.get('start_time', '')))

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