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
        """Load patients from a specific CSV file."""
        patients = []
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert timestamp string back to datetime if it exists
                    original_timestamp_str = row.get('timestamp', '') # Get original string
                    if 'timestamp' in row and row['timestamp']:
                        try:
                            # Attempt ISO format first
                            row['timestamp'] = datetime.datetime.fromisoformat(original_timestamp_str)
                        except ValueError:
                            # Fallback to trying other formats if needed (example)
                            # Or simply default to now if parsing fails broadly
                            print(f"Warning: Could not parse timestamp '{original_timestamp_str}' as ISO format for row: {row.get('name')}. Using current time.")
                            row['timestamp'] = datetime.datetime.now() # Fallback
                    else: # Handle case where timestamp column might be missing or empty
                         row['timestamp'] = datetime.datetime.now() # Fallback if column missing/empty

                    # --- Load availability_days ---
                    # Stored as comma-separated string in CSV, convert to list
                    availability_str = row.get('availability_days', '')
                    row['availability_days'] = [day.strip() for day in availability_str.split(',') if day.strip()] if availability_str else []
                    # --- End availability_days loading ---

                    # Ensure required fields exist, provide defaults if necessary
                    row.setdefault('id', str(uuid.uuid4()))
                    row.setdefault('name', row.get('name', 'Unknown')) # Use actual name if present
                    row.setdefault('phone', row.get('phone', 'N/A')) # Use actual phone if present
                    row.setdefault('email', row.get('email', ''))
                    row.setdefault('reason', row.get('reason', ''))
                    row.setdefault('urgency', row.get('urgency', 'medium'))
                    row.setdefault('appointment_type', row.get('appointment_type', 'consultation'))
                    row.setdefault('duration', row.get('duration', '30'))
                    # Use 'provider' column if present, otherwise default
                    row.setdefault('provider', row.get('provider', 'no preference'))
                    row.setdefault('status', 'waiting') # Default status if not in CSV
                    row.setdefault('wait_time', '0 minutes') # Default wait_time if not in CSV
                    # Timestamp is handled above

                    patients.append(row)
            return patients
        except FileNotFoundError:
            print(f"Warning: Backup file not found: {file_path}")
            return []
        except Exception as e:
            print(f"Error loading patients from {file_path}: {str(e)}")
            return [] # Return empty list on error

    def _save_timestamped_backup(self):
        """Save the current patient list to a new timestamped CSV file."""
        file_path = self._get_timestamped_filename()
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                # --- Add availability_days to fieldnames ---
                fieldnames = [
                    'id', 'name', 'phone', 'email', 'reason', 'urgency',
                    'appointment_type', 'duration', 'provider',
                    'status', 'timestamp', 'wait_time', 'availability_days' # Added
                ]
                # --- End fieldname update ---

                if not self.patients:
                    # Write headers even for empty file
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    print(f"Saved empty waitlist backup to: {file_path}")
                    return

                # Ensure all patient dicts have all keys for DictWriter
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()

                for patient in self.patients:
                    patient_copy = patient.copy()
                    # Convert datetime to ISO format string for CSV
                    if isinstance(patient_copy.get('timestamp'), datetime.datetime):
                        patient_copy['timestamp'] = patient_copy['timestamp'].isoformat()

                    # --- Convert availability_days list to comma-separated string ---
                    if isinstance(patient_copy.get('availability_days'), list):
                        patient_copy['availability_days'] = ','.join(patient_copy['availability_days'])
                    # --- End availability_days conversion ---

                    # Removed needs_dentist string conversion
                    # patient_copy['needs_dentist'] = str(patient_copy.get('needs_dentist', False))

                    # Write only the defined fieldnames
                    writer.writerow({k: patient_copy.get(k, '') for k in fieldnames})

            print(f"Saved waitlist backup to: {file_path}")
        except Exception as e:
            print(f"Error saving timestamped backup to {file_path}: {str(e)}")

    def add_patient(self, name: str, phone: str, email: str = "",
                   reason: str = "", urgency: str = "medium",
                   appointment_type: str = "consultation", duration: str = "30",
                   provider: str = "no preference",
                   availability_days: List[str] = None, # Added parameter
                   timestamp: Optional[datetime.datetime] = None) -> Optional[Dict[str, Any]]:
        """Adds a new patient with availability."""
        try:
            patient_id = str(uuid.uuid4())
            # Use provided timestamp or default to now
            entry_timestamp = timestamp if timestamp else datetime.datetime.now()
            # Use provided availability or default to empty list
            patient_availability = availability_days if availability_days is not None else []
            patient = {
                'id': patient_id,
                'name': name, 'phone': phone, 'email': email, 'reason': reason,
                'urgency': urgency, 'appointment_type': appointment_type,
                'duration': str(duration), # Ensure duration is string
                'provider': provider,
                'status': 'waiting', 'timestamp': entry_timestamp, 'wait_time': '0 minutes', # Use entry_timestamp
                'availability_days': patient_availability # Store the list
            }
            self.patients.append(patient)
            # self._save_timestamped_backup() # Ensure this is REMOVED/Commented
            return patient
        except Exception as e:
            print(f"Error adding patient: {e}")
            return None # Return None or raise exception

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

    def find_eligible_patients(self, provider_name: str, slot_duration: str, slot_day_of_week: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Finds eligible patients based on provider, duration, and day of the week availability.

        Args:
            provider_name (str): The name of the provider for the slot.
            slot_duration (str): The duration of the slot.
            slot_day_of_week (Optional[str]): The day of the week for the slot (e.g., 'Monday').
                                              If None, day availability is not checked.

        Returns:
            List[Dict[str, Any]]: A list of eligible patients, sorted by priority.
        """
        eligible_patients = []
        provider_matches = []
        no_preference_matches = []

        # Ensure slot duration is treated as string for comparison
        slot_duration_str = str(slot_duration)
        provider_name_lower = provider_name.lower() # Lowercase provider name once

        for patient in self.get_waiting_patients():
            # --- Filter Section ---
            # 1. Check Duration
            patient_duration = str(patient.get('duration', '0'))
            if patient_duration != slot_duration_str:
                continue # Skip if duration doesn't match

            # 2. Check Provider Preference
            patient_provider = patient.get('provider', '').strip().lower()
            is_provider_match = (patient_provider == provider_name_lower)
            is_no_preference = (patient_provider == 'no preference' or not patient_provider)

            if not (is_provider_match or is_no_preference):
                continue # Skip if provider doesn't match and isn't 'no preference'

            # 3. Check Day of Week Availability (if slot_day_of_week is provided)
            if slot_day_of_week:
                patient_availability = patient.get('availability_days', []) # Should be a list
                # Case-insensitive check if day name is in the list
                if not any(day.strip().lower() == slot_day_of_week.strip().lower() for day in patient_availability):
                    continue # Skip if patient is not available on this day

            # --- Add to intermediate lists ---
            if is_provider_match:
                provider_matches.append(patient)
            elif is_no_preference:
                no_preference_matches.append(patient)

        # Combine lists: specific provider matches first, then no preference
        eligible_patients = provider_matches + no_preference_matches

        # --- Sort Section ---
        urgency_order = {'high': 0, 'medium': 1, 'low': 2}
        emergency_str = 'emergency exam' # Define comparison string once

        eligible_patients.sort(key=lambda p: (
            # Primary key: Emergency status (0 for Emergency, 1 for others)
            0 if p.get('appointment_type', '').strip().lower() == emergency_str else 1,
            # Secondary key: Date added
            p.get('timestamp', datetime.datetime.min).date(),
            # Tertiary key: Urgency
            urgency_order.get(p.get('urgency', 'medium').strip().lower(), 1) # Default to medium
        ))
        return eligible_patients

    # Removed import_from_list as it conflicts with loading from latest backup
    # If migration is needed, it should be a separate script or handled carefully. 