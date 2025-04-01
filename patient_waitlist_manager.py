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
                    if 'timestamp' in row and row['timestamp']:
                        try:
                            row['timestamp'] = datetime.datetime.fromisoformat(row['timestamp'])
                        except ValueError:
                            row['timestamp'] = datetime.datetime.now() # Fallback

                    # Convert needs_dentist to boolean
                    if 'needs_dentist' in row:
                         row['needs_dentist'] = str(row['needs_dentist']).lower() in ['true', 'yes', '1', 'y']
                    else:
                         row['needs_dentist'] = False # Default if column missing

                    # Ensure required fields exist, provide defaults if necessary
                    row.setdefault('id', str(uuid.uuid4()))
                    row.setdefault('name', 'Unknown')
                    row.setdefault('phone', 'N/A')
                    row.setdefault('email', '')
                    row.setdefault('reason', '')
                    row.setdefault('urgency', 'medium')
                    row.setdefault('appointment_type', 'consultation')
                    row.setdefault('duration', '30')
                    row.setdefault('provider', 'no preference')
                    row.setdefault('status', 'waiting')
                    row.setdefault('wait_time', '0 minutes')
                    if 'timestamp' not in row:
                       row['timestamp'] = datetime.datetime.now()

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
                if not self.patients:
                    # Define headers even for empty file
                    fieldnames = [
                        'id', 'name', 'phone', 'email', 'reason', 'urgency',
                        'appointment_type', 'duration', 'provider', 'needs_dentist',
                        'status', 'timestamp', 'wait_time'
                    ]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    print(f"Saved empty waitlist backup to: {file_path}")
                    return

                # Use fieldnames from the first patient dict keys
                # Ensure consistent order - define standard headers
                fieldnames = [
                    'id', 'name', 'phone', 'email', 'reason', 'urgency',
                    'appointment_type', 'duration', 'provider', 'needs_dentist',
                    'status', 'timestamp', 'wait_time'
                ]
                # Ensure all patient dicts have all keys for DictWriter
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()

                for patient in self.patients:
                    patient_copy = patient.copy()
                    # Convert datetime to ISO format string for CSV
                    if isinstance(patient_copy.get('timestamp'), datetime.datetime):
                        patient_copy['timestamp'] = patient_copy['timestamp'].isoformat()
                    # Ensure boolean is saved as string
                    patient_copy['needs_dentist'] = str(patient_copy.get('needs_dentist', False))

                    # Write only the defined fieldnames
                    writer.writerow({k: patient_copy.get(k, '') for k in fieldnames})

            print(f"Saved waitlist backup to: {file_path}")
        except Exception as e:
            print(f"Error saving timestamped backup to {file_path}: {str(e)}")

    def add_patient(self, name: str, phone: str, email: str = "",
                   reason: str = "", urgency: str = "medium",
                   appointment_type: str = "consultation", duration: str = "30",
                   provider: str = "no preference", needs_dentist: bool = False,
                   timestamp: Optional[datetime.datetime] = None) -> Optional[Dict[str, Any]]:
        """Adds a new patient and triggers a timestamped backup."""
        try:
            patient_id = str(uuid.uuid4())
            # Use provided timestamp or default to now
            entry_timestamp = timestamp if timestamp else datetime.datetime.now()
            patient = {
                'id': patient_id,
                'name': name, 'phone': phone, 'email': email, 'reason': reason,
                'urgency': urgency, 'appointment_type': appointment_type,
                'duration': str(duration), # Ensure duration is string
                'provider': provider, 'needs_dentist': needs_dentist,
                'status': 'waiting', 'timestamp': entry_timestamp, 'wait_time': '0 minutes' # Use entry_timestamp
            }
            self.patients.append(patient)
            self._save_timestamped_backup() # Save after adding
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
                hours = delta.seconds // 3600
                minutes = (delta.seconds % 3600) // 60
                new_wait_time = '0 minutes'
                if days > 0:
                    new_wait_time = f"{days} days, {hours} hours"
                elif hours > 0:
                    new_wait_time = f"{hours} hours, {minutes} minutes"
                else:
                    new_wait_time = f"{minutes} minutes"

                if patient.get('wait_time') != new_wait_time:
                    patient['wait_time'] = new_wait_time
                    updated = True

        # Optional: Save only if wait times were actually updated
        # if updated:
        #     self._save_timestamped_backup() # Decided against saving on every time update call

    def schedule_patient(self, patient_id: str) -> bool:
        """Mark a patient as scheduled and save backup."""
        for patient in self.patients:
            if patient.get('id') == patient_id:
                if patient['status'] != 'scheduled':
                    patient['status'] = 'scheduled'
                    self._save_timestamped_backup() # Save after status change
                    return True
                return True # Already scheduled, count as success
        return False

    def remove_patient(self, patient_id: str) -> bool:
        """Remove a patient and save backup."""
        initial_len = len(self.patients)
        self.patients = [p for p in self.patients if p.get('id') != patient_id]
        if len(self.patients) < initial_len:
            self._save_timestamped_backup() # Save after removing
            return True
        return False

    def find_eligible_patients(self, provider_name: str) -> List[Dict[str, Any]]:
        # This method does not modify data, so no save needed here
        eligible_patients = []
        for patient in self.get_waiting_patients():
            if patient.get('provider', '').lower() == provider_name.lower():
                 eligible_patients.append(patient)
        for patient in self.get_waiting_patients():
             if (patient.get('provider', '').lower() == 'no preference' or not patient.get('provider')):
                 if not any(p['id'] == patient['id'] for p in eligible_patients):
                     eligible_patients.append(patient)
        # Sort by timestamp (wait time calculation happens elsewhere)
        eligible_patients.sort(key=lambda p: p.get('timestamp', datetime.datetime.min)) # Use min as default for sorting
        return eligible_patients

    # Removed import_from_list as it conflicts with loading from latest backup
    # If migration is needed, it should be a separate script or handled carefully. 