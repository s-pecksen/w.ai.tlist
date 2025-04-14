import os
import csv
import json
import datetime
from typing import List, Dict, Any, Optional
import uuid
import glob  # Needed for finding files

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
        # Define fieldnames early, including the new availability structure and mode
        self.fieldnames = [
            'id', 'name', 'phone', 'email', 'reason', 'urgency',
            'appointment_type', 'duration', 'provider',
            'status', 'timestamp', 'wait_time',
            'availability', # Stores JSON of day/time prefs
            'availability_mode' # Stores 'available' or 'unavailable'
        ]
        self._ensure_backup_dir_exists()
        self._cleanup_old_backups()

        # Load from the most recent backup
        latest_backup_path = self._get_latest_backup_path()
        if latest_backup_path:
            self.patients = self._load_patients(latest_backup_path)
            print(f"Loaded waitlist from: {latest_backup_path}")
        else:
            # No backups found, start with an empty list
            self.patients = []
            print("No existing waitlist backups found. Starting fresh.")
            # Optionally, save an initial empty backup
            self._save_timestamped_backup()

    def _ensure_backup_dir_exists(self):
        """Ensure the backup directory exists."""
        os.makedirs(self.backup_dir, exist_ok=True)

    def _get_timestamped_filename(self) -> str:
        """Generate a filename with a current timestamp."""
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
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
            print(f"Error finding latest backup: {e}")
            return None

    def _cleanup_old_backups(self, days_to_keep: int = 60):
        """Remove backup files older than the specified number of days."""
        cutoff = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
        try:
            for filename in glob.glob(os.path.join(self.backup_dir, 'waitlist_*.csv')):
                file_mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(filename))
                if file_mod_time < cutoff:
                    os.remove(filename)
                    print(f"Removed old backup: {filename}")
        except Exception as e:
            print(f"Error during backup cleanup: {e}")

    def _load_patients(self, file_path: str) -> List[Dict[str, Any]]:
        """Load patients from a specific CSV file, handling availability mode."""
        patients = []
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                # Basic header check - ensure 'id' and 'availability' exist at minimum
                # 'availability_mode' is optional for backward compatibility
                if not all(h in reader.fieldnames for h in ['id', 'availability']):
                    print(f"Warning: Missing essential headers ('id', 'availability') in {file_path}. Cannot load.")
                    return []

                has_mode_column = 'availability_mode' in reader.fieldnames

                for row in reader:
                    # Convert timestamp string back to datetime if it exists
                    original_timestamp_str = row.get('timestamp', '')
                    if 'timestamp' in row and row['timestamp']:
                        try:
                            row['timestamp'] = datetime.datetime.fromisoformat(original_timestamp_str)
                        except ValueError:
                            print(f"Warning: Could not parse timestamp '{original_timestamp_str}' as ISO format for row: {row.get('name')}. Using current time.")
                            row['timestamp'] = datetime.datetime.now()
                    else:
                         row['timestamp'] = datetime.datetime.now()

                    # --- Load availability (JSON dictionary) ---
                    availability_json_str = row.get('availability', '{}')
                    try:
                        loaded_avail = json.loads(availability_json_str)
                        if isinstance(loaded_avail, dict):
                             row['availability'] = {k: v for k, v in loaded_avail.items() if isinstance(v, list)}
                        else:
                             print(f"Warning: Parsed availability for {row.get('name')} is not a dictionary. Setting to empty.")
                             row['availability'] = {}
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse availability JSON '{availability_json_str}' for patient {row.get('name')}. Setting to empty.")
                        row['availability'] = {}

                    # --- Load availability_mode ---
                    if has_mode_column:
                         mode = row.get('availability_mode', 'available').lower()
                         # Validate the mode, default to 'available' if invalid
                         row['availability_mode'] = mode if mode in ['available', 'unavailable'] else 'available'
                    else:
                         # Default for older files without the column
                         row['availability_mode'] = 'available'
                    # --- End availability_mode loading ---


                    # Ensure required fields exist, provide defaults if necessary
                    row.setdefault('id', str(uuid.uuid4()))
                    row.setdefault('name', row.get('name', 'Unknown'))
                    row.setdefault('phone', row.get('phone', 'N/A'))
                    row.setdefault('email', row.get('email', ''))
                    row.setdefault('reason', row.get('reason', ''))
                    row.setdefault('urgency', row.get('urgency', 'medium'))
                    row.setdefault('appointment_type', row.get('appointment_type', 'consultation'))
                    row.setdefault('duration', row.get('duration', '30'))
                    row.setdefault('provider', row.get('provider', 'no preference'))
                    row.setdefault('status', 'waiting')
                    row.setdefault('wait_time', '0 minutes')

                    patients.append(row)
            return patients
        except FileNotFoundError:
            print(f"Warning: Backup file not found: {file_path}")
            return []
        except Exception as e:
            print(f"Error loading patients from {file_path}: {str(e)}")
            return []

    def _save_timestamped_backup(self):
        """Save the current patient list to a new timestamped CSV file, including availability mode."""
        file_path = self._get_timestamped_filename()
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                # Use the fieldnames defined in __init__ (which now includes availability_mode)
                fieldnames = self.fieldnames
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()

                if not self.patients:
                    print(f"Saved empty waitlist backup to: {file_path}")
                    return

                for patient in self.patients:
                    patient_copy = patient.copy()
                    # Convert datetime to ISO format string
                    if isinstance(patient_copy.get('timestamp'), datetime.datetime):
                        patient_copy['timestamp'] = patient_copy['timestamp'].isoformat()

                    # Convert availability dict to JSON string
                    if isinstance(patient_copy.get('availability'), dict):
                        patient_copy['availability'] = json.dumps(patient_copy['availability'])
                    else:
                        patient_copy['availability'] = json.dumps({})

                    # Ensure availability_mode is present (default if somehow missing)
                    patient_copy.setdefault('availability_mode', 'available')

                    # Write only the defined fieldnames
                    writer.writerow({k: patient_copy.get(k, '') for k in fieldnames})

            print(f"Saved waitlist backup to: {file_path}")
        except Exception as e:
            print(f"Error saving timestamped backup to {file_path}: {str(e)}")

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
            # Validate and normalize mode
            mode = availability_mode.lower() if availability_mode else 'available'
            valid_mode = mode if mode in ['available', 'unavailable'] else 'available'

            patient = {
                'id': patient_id,
                'name': name, 'phone': phone, 'email': email, 'reason': reason,
                'urgency': urgency, 'appointment_type': appointment_type,
                'duration': str(duration),
                'provider': provider,
                'status': 'waiting', 'timestamp': entry_timestamp, 'wait_time': '0 minutes',
                'availability': patient_availability,
                'availability_mode': valid_mode # Store validated mode
            }
            self.patients.append(patient)
            # self._save_timestamped_backup() # Manual save preferred
            return patient
        except Exception as e:
            print(f"Error adding patient: {e}")
            return None

    def get_all_patients(self) -> List[Dict[str, Any]]:
        """Get all patients currently loaded in memory."""
        return self.patients

    def get_waiting_patients(self) -> List[Dict[str, Any]]:
        """Get only patients with 'waiting' status."""
        return [p for p in self.patients if p.get('status') == 'waiting']

    def update_wait_times(self):
        """Update wait time for all waiting patients. Optionally save."""
        now = datetime.datetime.now()
        updated = False
        for patient in self.patients:
            if patient.get('status') == 'waiting' and 'timestamp' in patient:
                timestamp = patient['timestamp']
                # Handle if timestamp was loaded as string
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.datetime.fromisoformat(timestamp)
                        # Store the object back if successfully parsed
                        patient['timestamp'] = timestamp
                    except ValueError:
                        continue # Skip if parsing fails

                # Ensure timestamp is a datetime object before comparison
                if not isinstance(timestamp, datetime.datetime):
                    continue

                delta = now - timestamp
                days = delta.days
                # Simplified wait time: only show days
                new_wait_time = f"{days} days"

                if patient.get('wait_time') != new_wait_time:
                    patient['wait_time'] = new_wait_time
                    updated = True

        # Optional: Save only if wait times were actually updated
        # if updated:
        #     self._save_timestamped_backup() # Decided against saving on every time update call

    def schedule_patient(self, patient_id: str) -> bool:
        """Mark a patient as scheduled."""
        for patient in self.patients:
            if patient.get('id') == patient_id:
                if patient['status'] != 'scheduled':
                    patient['status'] = 'scheduled'
                    # self._save_timestamped_backup() # Ensure this is REMOVED/Commented
                    return True
                return True # Already scheduled, count as success
        return False

    def remove_patient(self, patient_id: str) -> bool:
        """Remove a patient."""
        initial_len = len(self.patients)
        self.patients = [p for p in self.patients if p.get('id') != patient_id]
        if len(self.patients) < initial_len:
            # self._save_timestamped_backup() # Ensure this is REMOVED/Commented
            return True
        return False

    def save_backup(self):
        """Manually trigger saving the current patient list to a timestamped backup file."""
        self._save_timestamped_backup() # This one STAYS for the manual button

    def find_eligible_patients(self, provider_name: str, slot_duration: str,
                               slot_day_of_week: Optional[str] = None,
                               slot_period: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Finds eligible patients based on provider, duration, day, time period (AM/PM),
        and patient's availability mode.

        Args:
            provider_name (str): The name of the provider for the slot.
            slot_duration (str): The duration of the slot.
            slot_day_of_week (Optional[str]): The day of the week (e.g., 'Monday').
            slot_period (Optional[str]): The time period ('AM' or 'PM').

        Returns:
            List[Dict[str, Any]]: A list of eligible patients, sorted by priority.
        """
        eligible_patients = []
        provider_matches = []
        no_preference_matches = []

        slot_duration_str = str(slot_duration)
        provider_name_lower = provider_name.lower()
        slot_day_lower = slot_day_of_week.strip().lower() if slot_day_of_week else None
        slot_period_upper = slot_period.strip().upper() if slot_period else None

        for patient in self.get_waiting_patients():
            # 1. Check Duration (Same as before)
            patient_duration = str(patient.get('duration', '0'))
            if patient_duration != slot_duration_str:
                continue

            # 2. Check Provider Preference (Same as before)
            patient_provider = patient.get('provider', '').strip().lower()
            is_provider_match = (patient_provider == provider_name_lower)
            is_no_preference = (patient_provider == 'no preference' or not patient_provider)
            if not (is_provider_match or is_no_preference):
                continue

            # 3. Check Day and Time Availability (with Mode Logic)
            patient_availability_prefs = patient.get('availability', {}) # The dict of day/time prefs
            # Default to 'available' if mode is missing for any reason
            patient_mode = patient.get('availability_mode', 'available')

            # Assume patient is available by default, then check conditions
            is_available_for_slot = True

            # Only apply checks if a specific day/period is being matched
            if slot_day_lower and slot_period_upper:
                # Does the patient have any preferences listed at all?
                has_preferences = bool(patient_availability_prefs)

                # Check if the specific slot day/time matches a preference
                slot_matches_preference = False
                if slot_day_lower in patient_availability_prefs:
                    day_prefs = patient_availability_prefs.get(slot_day_lower, [])
                    day_prefs_upper = [p.strip().upper() for p in day_prefs]
                    if slot_period_upper in day_prefs_upper or ('AM' in day_prefs_upper and 'PM' in day_prefs_upper):
                        slot_matches_preference = True

                # Apply mode logic:
                if patient_mode == 'available':
                    # Available Mode: Must match pref OR have no prefs listed
                    if has_preferences and not slot_matches_preference:
                        is_available_for_slot = False
                elif patient_mode == 'unavailable':
                    # Unavailable Mode: Must NOT match a listed preference
                    # (Having no preferences listed still means available)
                    if has_preferences and slot_matches_preference:
                        is_available_for_slot = False
                # else: mode is invalid, treat as 'available' (covered by default)

            # If the patient is determined unavailable by the checks, skip them
            if not is_available_for_slot:
                continue

            # --- Add to intermediate lists (Same as before) ---
            if is_provider_match:
                provider_matches.append(patient)
            elif is_no_preference:
                no_preference_matches.append(patient)

        # Combine lists (Same as before)
        eligible_patients = provider_matches + no_preference_matches

        # --- Sort Section (Same as before) ---
        urgency_order = {'high': 0, 'medium': 1, 'low': 2}
        emergency_str = 'emergency_exam'
        eligible_patients.sort(key=lambda p: (
            0 if p.get('appointment_type', '').strip().lower() == emergency_str else 1,
            p.get('timestamp', datetime.datetime.min).date(),
            urgency_order.get(p.get('urgency', 'medium').strip().lower(), 1)
        ))
        return eligible_patients

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