import os
import csv
import json
import datetime
from typing import List, Dict, Any, Optional
import uuid
import glob  # Needed for finding files
import logging # Use logging instead of print

class PatientWaitlistManager:
    def __init__(self, app_name: str, backup_dir: str = 'waitlist_backups'):
        """
        Initialize the Patient Waitlist Manager using timestamped backups.

        Args:
            app_name (str): Name of the application.
            backup_dir (str): Directory to store timestamped CSV backups.
        """
        self.app_name = app_name
        self.backup_dir = backup_dir
        # Define fieldnames early, including availability, mode, and proposed slot
        self.fieldnames = [
            'id', 'name', 'phone', 'email', 'reason', 'urgency',
            'appointment_type', 'duration', 'provider',
            'status', 'timestamp', 'wait_time',
            'availability', # Stores JSON of day/time prefs
            'availability_mode', # Stores 'available' or 'unavailable'
            'proposed_slot_id' # Stores the ID of the slot proposed to the patient
        ]
        # Define valid statuses
        self.valid_statuses = ['waiting', 'scheduled', 'awaiting confirmation']

        self._ensure_backup_dir_exists()
        self._cleanup_old_backups()

        # Load from the most recent backup
        latest_backup_path = self._get_latest_backup_path()
        if latest_backup_path:
            self.patients = self._load_patients(latest_backup_path)
            logging.info(f"Loaded waitlist from: {latest_backup_path}")
        else:
            # No backups found, start with an empty list
            self.patients = []
            logging.info("No existing waitlist backups found. Starting fresh.")
            # Optionally, save an initial empty backup
            self._save_timestamped_backup()

    def _ensure_backup_dir_exists(self):
        """Ensure the backup directory exists."""
        os.makedirs(self.backup_dir, exist_ok=True)

    def _get_timestamped_filename(self) -> str:
        """Generate a filename with a current timestamp."""
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S_%f") # Use microseconds for uniqueness
        return os.path.join(self.backup_dir, f"waitlist_{timestamp_str}.csv")

    def _get_latest_backup_path(self) -> Optional[str]:
        """Find the most recent CSV backup file in the backup directory."""
        try:
            list_of_files = glob.glob(os.path.join(self.backup_dir, 'waitlist_*.csv'))
            if not list_of_files:
                return None
            latest_file = max(list_of_files, key=os.path.getctime)
            return latest_file
        except Exception as e:
            logging.error(f"Error finding latest backup: {e}", exc_info=True)
            return None

    def _cleanup_old_backups(self, days_to_keep: int = 60):
        """Remove backup files older than the specified number of days."""
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
        try:
            for filename in glob.glob(os.path.join(self.backup_dir, 'waitlist_*.csv')):
                try:
                    file_mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(filename))
                    if file_mod_time < cutoff:
                        os.remove(filename)
                        logging.info(f"Removed old backup: {filename}")
                except OSError as e:
                    logging.warning(f"Error removing old backup file {filename}: {e}")
        except Exception as e:
            logging.error(f"Error during backup cleanup: {e}", exc_info=True)

    def _load_patients(self, file_path: str) -> List[Dict[str, Any]]:
        """Load patients from a specific CSV file, handling new fields."""
        patients = []
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []

                # Check for minimum essential headers for basic functionality
                if 'id' not in headers:
                    logging.error(f"Critical header 'id' missing in {file_path}. Cannot load.")
                    return []

                has_availability_col = 'availability' in headers
                has_mode_column = 'availability_mode' in headers
                has_proposed_col = 'proposed_slot_id' in headers

                for row in reader:
                    # Convert timestamp string back to datetime if it exists
                    original_timestamp_str = row.get('timestamp', '')
                    if original_timestamp_str:
                        try:
                            row['timestamp'] = datetime.datetime.fromisoformat(original_timestamp_str)
                        except ValueError:
                            logging.warning(f"Could not parse timestamp '{original_timestamp_str}' as ISO format for row: {row.get('name')}. Using current time.")
                            row['timestamp'] = datetime.datetime.now()
                    else:
                         row['timestamp'] = datetime.datetime.now() # Assign timestamp if missing

                    # --- Load availability (JSON dictionary) ---
                    if has_availability_col:
                        availability_json_str = row.get('availability', '{}')
                        try:
                            loaded_avail = json.loads(availability_json_str)
                            row['availability'] = loaded_avail if isinstance(loaded_avail, dict) else {}
                        except json.JSONDecodeError:
                            logging.warning(f"Could not parse availability JSON '{availability_json_str}' for patient {row.get('name')}. Setting to empty.")
                            row['availability'] = {}
                    else:
                         row['availability'] = {}

                    # --- Load availability_mode ---
                    if has_mode_column:
                         mode = row.get('availability_mode', 'available').lower()
                         row['availability_mode'] = mode if mode in ['available', 'unavailable'] else 'available'
                    else:
                         row['availability_mode'] = 'available'

                    # --- Load proposed_slot_id ---
                    row['proposed_slot_id'] = row.get('proposed_slot_id', '') if has_proposed_col else ''

                    # --- Load Status and Validate ---
                    status = row.get('status', 'waiting').lower()
                    row['status'] = status if status in self.valid_statuses else 'waiting'


                    # Ensure other required fields exist, provide defaults if necessary
                    row.setdefault('name', 'Unknown')
                    row.setdefault('phone', 'N/A')
                    row.setdefault('email', '')
                    row.setdefault('reason', '')
                    row.setdefault('urgency', 'medium')
                    row.setdefault('appointment_type', 'consultation')
                    row.setdefault('duration', '30')
                    row.setdefault('provider', 'no preference')
                    row.setdefault('wait_time', '0 minutes')

                    patients.append(row)
            return patients
        except FileNotFoundError:
            logging.warning(f"Backup file not found: {file_path}")
            return []
        except Exception as e:
            logging.error(f"Error loading patients from {file_path}: {str(e)}", exc_info=True)
            return []

    def _save_timestamped_backup(self):
        """Save the current patient list to a new timestamped CSV file."""
        file_path = self._get_timestamped_filename()
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                # Use the fieldnames defined in __init__
                writer = csv.DictWriter(f, fieldnames=self.fieldnames, extrasaction='ignore')
                writer.writeheader()

                if not self.patients:
                    logging.info(f"Saved empty waitlist backup to: {file_path}")
                    return

                for patient in self.patients:
                    patient_copy = patient.copy()
                    # Convert datetime to ISO format string
                    if isinstance(patient_copy.get('timestamp'), datetime.datetime):
                        patient_copy['timestamp'] = patient_copy['timestamp'].isoformat()
                    else: # Handle potential None or already string cases
                        patient_copy['timestamp'] = ''

                    # Convert availability dict to JSON string
                    patient_copy['availability'] = json.dumps(patient_copy.get('availability', {}))

                    # Ensure all fieldnames are present before writing
                    for field in self.fieldnames:
                        patient_copy.setdefault(field, '')

                    writer.writerow(patient_copy)

            logging.info(f"Saved {len(self.patients)} patients backup to: {file_path}")
        except Exception as e:
            logging.error(f"Error saving timestamped backup to {file_path}: {str(e)}", exc_info=True)

    def add_patient(self, name: str, phone: str, email: str = "",
                   reason: str = "", urgency: str = "medium",
                   appointment_type: str = "consultation", duration: str = "30",
                   provider: str = "no preference",
                   availability: Optional[Dict[str, List[str]]] = None,
                   availability_mode: str = 'available', # Added parameter
                   timestamp: Optional[datetime.datetime] = None) -> Optional[Dict[str, Any]]:
        """Adds a new patient with structured availability and mode."""
        try:
            patient_id = str(uuid.uuid4())
            entry_timestamp = timestamp if timestamp else datetime.datetime.now()
            patient_availability = availability if availability is not None else {}
            mode = availability_mode.lower() if availability_mode else 'available'
            valid_mode = mode if mode in ['available', 'unavailable'] else 'available'

            patient = {
                'id': patient_id,
                'name': name, 'phone': phone, 'email': email, 'reason': reason,
                'urgency': urgency, 'appointment_type': appointment_type,
                'duration': str(duration),
                'provider': provider,
                'status': 'waiting', # New patients start as waiting
                'timestamp': entry_timestamp, 'wait_time': '0 minutes',
                'availability': patient_availability,
                'availability_mode': valid_mode,
                'proposed_slot_id': '' # Initialize as empty
            }
            self.patients.append(patient)
            self.save_backup() # Save after adding a patient
            logging.info(f"Added patient {patient_id} ({name}).")
            return patient
        except Exception as e:
            logging.error(f"Error adding patient: {e}", exc_info=True)
            return None

    def get_all_patients(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get patients, optionally filtering by status."""
        if status_filter:
            status_filter_lower = status_filter.lower()
            if status_filter_lower not in self.valid_statuses:
                logging.warning(f"Invalid status filter '{status_filter}'. Returning all patients.")
                return self.patients
            return [p for p in self.patients if p.get('status', '').lower() == status_filter_lower]
        return self.patients

    def update_wait_times(self):
        """Update wait time for all non-scheduled patients."""
        now = datetime.datetime.now()
        updated = False
        for patient in self.patients:
            # Update for waiting and awaiting confirmation
            if patient.get('status') in ['waiting', 'awaiting confirmation'] and isinstance(patient.get('timestamp'), datetime.datetime):
                delta = now - patient['timestamp']
                days = delta.days
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, _ = divmod(remainder, 60)

                # Build wait time string (e.g., "5 days, 3 hours" or "1 hour, 30 minutes")
                wait_parts = []
                if days > 0:
                    wait_parts.append(f"{days} day{'s' if days != 1 else ''}")
                if hours > 0:
                     wait_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
                if not wait_parts and minutes >= 0: # Show minutes if less than an hour wait
                     wait_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

                new_wait_time = ", ".join(wait_parts) if wait_parts else "0 minutes"

                if patient.get('wait_time') != new_wait_time:
                    patient['wait_time'] = new_wait_time
                    updated = True
            elif patient.get('status') == 'scheduled':
                # Clear wait time for scheduled patients
                if patient.get('wait_time') != '':
                    patient['wait_time'] = ''
                    updated = True

        # No automatic save on wait time update

    def update_patient_status(self, patient_id: str, new_status: str, proposed_slot_id: Optional[str] = None) -> bool:
        """
        Updates the status of a specific patient and optionally their proposed slot ID.

        Args:
            patient_id (str): The ID of the patient to update.
            new_status (str): The new status (must be one of self.valid_statuses).
            proposed_slot_id (Optional[str]): The ID of the slot being proposed or None/empty to clear.

        Returns:
            bool: True if the patient was found and updated, False otherwise.
        """
        new_status_lower = new_status.lower()
        if new_status_lower not in self.valid_statuses:
            logging.error(f"Attempted to set invalid status '{new_status}' for patient {patient_id}.")
            return False

        patient_found = False
        for i, patient in enumerate(self.patients):
            if patient.get('id') == patient_id:
                # Update status
                self.patients[i]['status'] = new_status_lower

                # Update proposed_slot_id based on status
                if new_status_lower == 'awaiting confirmation':
                    self.patients[i]['proposed_slot_id'] = proposed_slot_id if proposed_slot_id else ''
                    logging.debug(f"Set patient {patient_id} status to 'awaiting confirmation' for slot {proposed_slot_id}")
                else:
                    # Clear proposed slot ID if status is not awaiting confirmation
                    if self.patients[i].get('proposed_slot_id'):
                         logging.debug(f"Clearing proposed slot ID for patient {patient_id} due to status change to '{new_status_lower}'")
                    self.patients[i]['proposed_slot_id'] = ''

                # Clear wait time if scheduled
                if new_status_lower == 'scheduled':
                    self.patients[i]['wait_time'] = ''

                patient_found = True
                break # Exit loop once patient is found

        if patient_found:
            self.save_backup() # Save after modifying status
            logging.info(f"Updated patient {patient_id} status to '{new_status_lower}'.")
        else:
            logging.warning(f"Could not update status for patient {patient_id}: Patient not found.")

        return patient_found


    # Keep schedule_patient and remove_patient simple, status changes handled by update_patient_status
    def schedule_patient(self, patient_id: str) -> bool:
        """Mark a patient as scheduled (uses update_patient_status)."""
        return self.update_patient_status(patient_id, 'scheduled')

    def remove_patient(self, patient_id: str) -> bool:
        """Remove a patient and save."""
        initial_len = len(self.patients)
        self.patients = [p for p in self.patients if p.get('id') != patient_id]
        if len(self.patients) < initial_len:
            self.save_backup() # Save after removing a patient
            logging.info(f"Removed patient {patient_id}.")
            return True
        logging.warning(f"Attempted to remove non-existent patient ID: {patient_id}")
        return False

    def save_backup(self):
        """Manually trigger saving the current patient list to a timestamped backup file."""
        self._save_timestamped_backup()

    # Simplified find_eligible_patients - relies on get_all_patients(status='waiting')
    def find_eligible_patients(self, provider_name: str, slot_duration: str,
                               slot_day_of_week: Optional[str] = None,
                               slot_period: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Finds eligible WAITING patients based on provider, duration, day, time period (AM/PM),
        and patient's availability mode. Excludes patients awaiting confirmation.
        """
        eligible_patients = []
        provider_matches = []
        no_preference_matches = []

        slot_duration_str = str(slot_duration)
        provider_name_lower = provider_name.lower()
        slot_day_lower = slot_day_of_week.strip().lower() if slot_day_of_week else None
        slot_period_upper = slot_period.strip().upper() if slot_period else None

        # Get only patients currently in 'waiting' status
        for patient in self.get_all_patients(status_filter='waiting'):
            # 1. Check Duration
            if str(patient.get('duration', '0')) != slot_duration_str:
                continue

            # 2. Check Provider Preference
            patient_provider = patient.get('provider', '').strip().lower()
            is_provider_match = (patient_provider == provider_name_lower)
            is_no_preference = (patient_provider == 'no preference' or not patient_provider)
            if not (is_provider_match or is_no_preference):
                continue

            # 3. Check Day and Time Availability (with Mode Logic)
            patient_availability_prefs = patient.get('availability', {})
            patient_mode = patient.get('availability_mode', 'available')
            is_available_for_slot = True

            if slot_day_lower and slot_period_upper:
                has_preferences = bool(patient_availability_prefs)
                slot_matches_preference = False
                # Find matching day key case-insensitively
                matching_day_key = next((k for k in patient_availability_prefs if k.lower() == slot_day_lower), None)

                if matching_day_key:
                    day_prefs = patient_availability_prefs.get(matching_day_key, [])
                    day_prefs_upper = [str(p).strip().upper() for p in day_prefs]
                    if slot_period_upper in day_prefs_upper:
                        slot_matches_preference = True

                if patient_mode == 'available':
                    if has_preferences and not slot_matches_preference:
                        is_available_for_slot = False
                elif patient_mode == 'unavailable':
                    if has_preferences and slot_matches_preference:
                        is_available_for_slot = False

            if not is_available_for_slot:
                continue

            # Add to intermediate lists
            if is_provider_match:
                provider_matches.append(patient)
            elif is_no_preference:
                no_preference_matches.append(patient)

        # Combine lists and sort
        eligible_patients = provider_matches + no_preference_matches
        urgency_order = {'high': 0, 'medium': 1, 'low': 2}
        emergency_str = 'emergency_exam'
        eligible_patients.sort(key=lambda p: (
            0 if p.get('appointment_type', '').strip().lower() == emergency_str else 1, # Emergency first
            urgency_order.get(p.get('urgency', 'medium').strip().lower(), 1), # Then urgency
            p.get('timestamp', datetime.datetime.max) # Then timestamp (earlier first)
        ))

        return eligible_patients


    def get_patient_by_id(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Finds a patient by their unique ID."""
        for patient in self.patients:
            if patient.get('id') == patient_id:
                return patient
        return None

    def update_patient(self, patient_id: str, updated_data: Dict[str, Any]) -> bool:
        """
        Updates an existing patient's editable data fields. Status is handled separately.
        """
        patient_found = False
        for i, patient in enumerate(self.patients):
            if patient.get('id') == patient_id:
                # Update only editable fields from the form
                self.patients[i]['name'] = updated_data.get('name', patient.get('name'))
                self.patients[i]['phone'] = updated_data.get('phone', patient.get('phone'))
                self.patients[i]['email'] = updated_data.get('email', patient.get('email'))
                self.patients[i]['reason'] = updated_data.get('reason', patient.get('reason'))
                self.patients[i]['urgency'] = updated_data.get('urgency', patient.get('urgency'))
                self.patients[i]['appointment_type'] = updated_data.get('appointment_type', patient.get('appointment_type'))
                self.patients[i]['duration'] = str(updated_data.get('duration', patient.get('duration')))
                self.patients[i]['provider'] = updated_data.get('provider', patient.get('provider'))

                # Handle availability update
                availability = updated_data.get('availability')
                self.patients[i]['availability'] = availability if isinstance(availability, dict) else patient.get('availability', {})

                # Handle availability mode update
                mode = updated_data.get('availability_mode', patient.get('availability_mode', 'available')).lower()
                self.patients[i]['availability_mode'] = mode if mode in ['available', 'unavailable'] else 'available'

                # Do NOT update status, timestamp, wait_time, or proposed_slot_id here
                patient_found = True
                logging.info(f"Updated editable details for patient {patient_id}.")
                break # Exit loop once patient is found and updated

        if patient_found:
             self.save_backup() # Save after editing patient details
        else:
             logging.warning(f"Could not update patient details for {patient_id}: Patient not found.")

        return patient_found

    # Removed import_from_list as it conflicts with loading from latest backup
    # If migration is needed, it should be a separate script or handled carefully.

    # --- Add get_patient_by_id needed by app.py ---
    def get_patient_by_id(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Finds a patient by their unique ID."""
        for patient in self.patients:
            if patient.get('id') == patient_id:
                return patient
        return None
    # --- End get_patient_by_id ---

    # --- Add update_patient method ---
    def update_patient(self, patient_id: str, updated_data: Dict[str, Any]) -> bool:
        """
        Updates an existing patient's data.

        Args:
            patient_id (str): The ID of the patient to update.
            updated_data (Dict[str, Any]): A dictionary containing the fields to update.
                                         Expected keys match form fields plus processed
                                         'availability' dict and 'availability_mode' string.

        Returns:
            bool: True if the patient was found and updated, False otherwise.
        """
        patient_found = False
        for i, patient in enumerate(self.patients):
            if patient.get('id') == patient_id:
                # Preserve original ID and timestamp
                original_id = patient.get('id')
                original_timestamp = patient.get('timestamp')
                original_status = patient.get('status') # Keep original status (e.g., 'waiting')
                original_wait_time = patient.get('wait_time') # Keep calculated wait time

                # Update the patient dictionary with new data
                # Make sure availability is stored as a dictionary
                availability = updated_data.get('availability')
                if not isinstance(availability, dict):
                     availability = {} # Default to empty dict if not provided correctly

                # Validate and normalize mode
                mode = updated_data.get('availability_mode', 'available').lower()
                valid_mode = mode if mode in ['available', 'unavailable'] else 'available'

                # Construct the updated patient record
                updated_patient = {
                    'id': original_id,
                    'name': updated_data.get('name', patient.get('name')),
                    'phone': updated_data.get('phone', patient.get('phone')),
                    'email': updated_data.get('email', patient.get('email', '')),
                    'reason': updated_data.get('reason', patient.get('reason', '')),
                    'urgency': updated_data.get('urgency', patient.get('urgency')),
                    'appointment_type': updated_data.get('appointment_type', patient.get('appointment_type')),
                    'duration': str(updated_data.get('duration', patient.get('duration'))),
                    'provider': updated_data.get('provider', patient.get('provider')),
                    'availability': availability,
                    'availability_mode': valid_mode,
                    'timestamp': original_timestamp, # Keep original timestamp
                    'status': original_status,       # Keep original status
                    'wait_time': original_wait_time  # Keep calculated wait time
                }
                self.patients[i] = updated_patient
                patient_found = True
                break # Exit loop once patient is found and updated

        return patient_found
    # --- End update_patient method --- 