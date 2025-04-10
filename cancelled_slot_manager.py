import os
import csv
import uuid
from datetime import datetime
import glob
import shutil
import logging

class CancelledSlotManager:
    """Manages cancelled appointment slots, persisting them to CSV files."""

    def __init__(self, backup_dir='cancelled_slots_backups'):
        self.backup_dir = backup_dir
        self.slots_file_prefix = "cancelled_slots_"
        self.slots_file_suffix = ".csv"
        self.slots = []  # In-memory list of slot dictionaries
        self.headers = ['id', 'provider', 'duration', 'notes', 'matched_patient_id', 'matched_patient_name'] # Define CSV headers

        os.makedirs(self.backup_dir, exist_ok=True)
        self._load_slots()
        logging.info(f"CancelledSlotManager initialized. Loaded {len(self.slots)} slots.")

    def _get_latest_backup(self):
        """Finds the most recent backup file."""
        try:
            list_of_files = glob.glob(os.path.join(self.backup_dir, f'{self.slots_file_prefix}*{self.slots_file_suffix}'))
            if not list_of_files:
                return None
            latest_file = max(list_of_files, key=os.path.getctime)
            return latest_file
        except Exception as e:
            logging.error(f"Error finding latest cancelled slots backup: {e}", exc_info=True)
            return None

    def _load_slots(self):
        """Loads slots from the latest CSV backup file."""
        latest_backup = self._get_latest_backup()
        if latest_backup and os.path.exists(latest_backup):
            try:
                with open(latest_backup, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    if reader.fieldnames != self.headers:
                         # Handle potential header mismatch or older format if necessary
                         logging.warning(f"Header mismatch in {latest_backup}. Expected {self.headers}, got {reader.fieldnames}. Attempting load anyway.")
                         # Basic check: ensure essential 'id' is present
                         if 'id' not in reader.fieldnames:
                             logging.error("Critical header 'id' missing. Cannot load slots.")
                             self.slots = []
                             return

                    loaded_slots = []
                    for row in reader:
                        # Reconstruct matched_patient dictionary
                        matched_patient = None
                        if row.get('matched_patient_id') and row.get('matched_patient_name'):
                             matched_patient = {
                                 'id': row.get('matched_patient_id'),
                                 'name': row.get('matched_patient_name')
                             }
                        # Build the slot dictionary using known headers, handling missing optional ones
                        slot = {
                            'id': row.get('id'), # Required
                            'provider': row.get('provider'), # Required (assuming)
                            'duration': row.get('duration'), # Required (assuming)
                            'notes': row.get('notes', ''), # Optional
                            'matched_patient': matched_patient # Reconstructed or None
                        }
                        if slot['id'] and slot['provider'] and slot['duration']: # Basic validation
                             loaded_slots.append(slot)
                        else:
                            logging.warning(f"Skipping row due to missing essential data: {row}")

                    self.slots = loaded_slots
                    logging.info(f"Successfully loaded {len(self.slots)} slots from {latest_backup}")

            except FileNotFoundError:
                 logging.warning(f"Latest backup file {latest_backup} not found during load attempt.")
                 self.slots = []
            except Exception as e:
                logging.error(f"Error loading cancelled slots from {latest_backup}: {e}", exc_info=True)
                self.slots = [] # Clear list on error to avoid partial loads
        else:
            logging.info("No existing cancelled slots backup found. Starting with an empty list.")
            self.slots = []

    def _save_slots(self):
        """Saves the current list of slots to a new timestamped CSV file."""
        if not self.slots: # Don't save empty files if list is empty
             # Optional: Consider removing old backups if the list becomes empty
             # logging.info("Slot list is empty. Skipping save.")
             # return # Or proceed to save an empty file if desired
             pass # Let's save an empty file for consistency

        now = datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S_%f") # Added microseconds for uniqueness
        filename = f"{self.slots_file_prefix}{timestamp_str}{self.slots_file_suffix}"
        filepath = os.path.join(self.backup_dir, filename)

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.headers)
                writer.writeheader()
                for slot in self.slots:
                    # Prepare row, flattening matched_patient
                    row_data = {
                        'id': slot.get('id'),
                        'provider': slot.get('provider'),
                        'duration': slot.get('duration'),
                        'notes': slot.get('notes', ''),
                        'matched_patient_id': slot.get('matched_patient', {}).get('id', '') if slot.get('matched_patient') else '',
                        'matched_patient_name': slot.get('matched_patient', {}).get('name', '') if slot.get('matched_patient') else ''
                    }
                    writer.writerow(row_data)
            logging.info(f"Successfully saved {len(self.slots)} slots to {filepath}")
            # Optional: Implement backup rotation/cleanup here
        except Exception as e:
            logging.error(f"Error saving cancelled slots to {filepath}: {e}", exc_info=True)

    def add_slot(self, provider, duration, notes=''):
        """Adds a new cancelled slot and saves the list."""
        new_id = str(uuid.uuid4())
        new_slot = {
            'id': new_id,
            'provider': provider,
            'duration': str(duration), # Ensure duration is stored as string
            'notes': notes, # Use the provided notes, or the default ''
            'matched_patient': None
        }
        self.slots.append(new_slot)
        self._save_slots()
        logging.debug(f"Added slot {new_id}. Total slots: {len(self.slots)}")
        return new_slot # Return the created slot with its ID

    def remove_slot(self, appointment_id):
        """Removes a slot by its ID and saves the list."""
        initial_length = len(self.slots)
        self.slots = [slot for slot in self.slots if slot.get('id') != appointment_id]
        if len(self.slots) < initial_length:
            self._save_slots()
            logging.debug(f"Removed slot {appointment_id}. Total slots: {len(self.slots)}")
            return True
        logging.warning(f"Attempted to remove non-existent slot ID: {appointment_id}")
        return False

    def update_slot(self, appointment_id, provider, duration, notes):
        """Updates details of an existing slot and saves the list."""
        updated = False
        for i, slot in enumerate(self.slots):
            if slot.get('id') == appointment_id:
                 # Don't allow updating matched slots through this method
                 if slot.get('matched_patient'):
                     logging.warning(f"Attempted to update already matched slot {appointment_id} via update_slot.")
                     return False # Or raise an error

                 self.slots[i]['provider'] = provider
                 self.slots[i]['duration'] = str(duration) # Ensure duration is string
                 self.slots[i]['notes'] = notes
                 updated = True
                 break
        if updated:
            self._save_slots()
            logging.debug(f"Updated slot {appointment_id}.")
        else:
             logging.warning(f"Attempted to update non-existent or matched slot ID: {appointment_id}")
        return updated

    def assign_patient_to_slot(self, appointment_id, patient_data):
        """Marks a slot as matched with a patient and saves."""
        assigned = False
        for i, slot in enumerate(self.slots):
            if slot.get('id') == appointment_id:
                if slot.get('matched_patient'):
                     logging.warning(f"Slot {appointment_id} is already assigned to {slot['matched_patient'].get('name')}. Overwriting.")
                # Store only essential patient info
                self.slots[i]['matched_patient'] = {
                    'id': patient_data.get('id'),
                    'name': patient_data.get('name')
                }
                assigned = True
                break
        if assigned:
            self._save_slots()
            logging.debug(f"Assigned patient {patient_data.get('id')} to slot {appointment_id}.")
        else:
            logging.error(f"Failed to assign patient: Slot {appointment_id} not found.")

        return assigned


    def get_slot_by_id(self, appointment_id):
        """Retrieves a single slot by its ID."""
        for slot in self.slots:
            if slot.get('id') == appointment_id:
                return slot
        return None

    def get_all_slots(self):
        """Returns a copy of the list of all slots."""
        # Return a copy to prevent external modification of the internal list
        return [slot.copy() for slot in self.slots] 