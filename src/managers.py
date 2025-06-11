import os
import csv
import json
from datetime import datetime
import logging
from typing import List, Dict, Any, Optional
import uuid

# Import the encryption helper functions
from .encryption_utils import load_decrypted_csv, save_encrypted_csv


class CancelledSlotManager:
    """Manages cancelled appointment slots, persisting them to CSV files."""

    def __init__(self, slots_file="cancelled.csv"):
        """Initialize with file paths."""
        self.slots_file = slots_file
        self.slots = []
        self.headers = [
            "id",
            "provider",
            "duration",
            "slot_date",
            "slot_period",
            "slot_time",
            "notes",
            "status",
            "proposed_patient_id",
            "proposed_patient_name",
        ]
        self.load()
        logging.info(f"Initialized CancelledSlotManager with {len(self.slots)} slots")

    def load(self):
        """Load slots from the CSV file."""
        try:
            # Use the decryption helper
            self.slots = load_decrypted_csv(self.slots_file, self.headers)
            logging.info(f"Loaded {len(self.slots)} slots from {self.slots_file}")
            for slot in self.slots:
                logging.debug(f"Loaded slot: {slot}")
        except Exception as e:
            logging.error(f"Error loading or decrypting slots: {e}", exc_info=True)
            self.slots = []

    def update(self):
        """Save the current slots to the CSV file."""
        try:
            # Use the encryption helper
            save_encrypted_csv(self.slots, self.slots_file, self.headers)
            logging.info(f"Updated {len(self.slots)} slots to {self.slots_file}")
            return True
        except Exception as e:
            logging.error(f"Error updating or encrypting slots: {e}", exc_info=True)
            return False

    def get_all_slots(self):
        """Return all slots."""
        logging.info(f"Returning {len(self.slots)} slots")
        return self.slots

    def add_slot(self, provider, slot_date, slot_time, slot_period, duration, notes=""):
        """Add a new cancelled appointment slot."""
        # Generate a unique ID
        slot_id = str(uuid.uuid4())

        # Create a new slot
        slot = {
            "id": slot_id,
            "provider": provider,
            "duration": duration,
            "slot_date": slot_date,
            "slot_period": slot_period,
            "slot_time": slot_time,
            "notes": notes,
            "status": "available",
            "proposed_patient_id": "",
            "proposed_patient_name": "",
        }

        # Add to the list
        self.slots.append(slot)

        # Save to file
        self.update()

        return True

    def remove_slot(self, slot_id):
        """Remove a cancelled appointment slot."""
        # Find the slot by ID
        initial_count = len(self.slots)
        self.slots = [s for s in self.slots if s.get("id") != slot_id]

        if len(self.slots) < initial_count:
            self.update()
            return True
        return False

    def update_slot(
        self, slot_id, provider, slot_date, slot_time, slot_period, duration, notes=""
    ):
        """Update an existing cancelled appointment slot."""
        # Find the slot by ID
        slot_index = None
        for i, slot in enumerate(self.slots):
            if slot.get("id") == slot_id:
                slot_index = i
                break

        if slot_index is None:
            return False  # Slot not found

        # Update the slot's details
        self.slots[slot_index].update(
            {
                "provider": provider,
                "duration": duration,
                "slot_date": slot_date,
                "slot_period": slot_period,
                "slot_time": slot_time,
                "notes": notes,
                "status": "available",
                "proposed_patient_id": "",
                "proposed_patient_name": "",
            }
        )

        # Save to file
        self.update()

        return True

    def mark_as_pending(self, slot_id, patient_id, patient_name="Unknown"):
        """Mark a slot as pending for a specific patient."""
        slot_index = -1
        for i, slot in enumerate(self.slots):
            if slot.get("id") == slot_id:
                slot_index = i
                break

        if slot_index == -1 or self.slots[slot_index].get("status") != "available":
            logging.warning(f"Cannot mark slot {slot_id} as pending. Not found or not available.")
            return False

        self.slots[slot_index]["status"] = "pending"
        self.slots[slot_index]["proposed_patient_id"] = patient_id
        self.slots[slot_index]["proposed_patient_name"] = patient_name
        self.update()
        logging.info(f"Marked slot {slot_id} as pending for patient {patient_id}")
        return True

    def cancel_proposal(self, slot_id):
        """Reset a pending slot back to available."""
        slot_index = -1
        for i, slot in enumerate(self.slots):
            if slot.get("id") == slot_id:
                slot_index = i
                break

        if slot_index == -1 or self.slots[slot_index].get("status") != "pending":
            logging.warning(f"Cannot cancel proposal for slot {slot_id}. Not found or not pending.")
            return False

        self.slots[slot_index]["status"] = "available"
        self.slots[slot_index]["proposed_patient_id"] = ""
        self.slots[slot_index]["proposed_patient_name"] = ""
        self.update()
        logging.info(f"Cancelled proposal for slot {slot_id}. Status reset to available.")
        return True

    def mark_as_filled(self, slot_id):
        """Mark a slot as filled (optional if keeping history)."""
        slot_index = -1
        for i, slot in enumerate(self.slots):
            if slot.get("id") == slot_id:
                slot_index = i
                break

        if slot_index == -1 or self.slots[slot_index].get("status") != "pending":
             logging.warning(f"Cannot mark slot {slot_id} as filled. Not found or not pending.")
             return False

        self.slots[slot_index]["status"] = "filled"
        self.update()
        logging.info(f"Marked slot {slot_id} as filled.")
        return True


class PatientWaitlistManager:
    """Manages the patient waitlist, persisting to CSV files."""

    def __init__(self, waitlist_file="waitlist.csv"):
        """Initialize with file paths."""
        self.waitlist_file = waitlist_file
        self.patients = []
        self.fieldnames = [
            "id",
            "name",
            "phone",
            "email",
            "reason",
            "urgency",
            "appointment_type",
            "duration",
            "provider",
            "status",
            "timestamp",
            "wait_time",
            "availability",
            "availability_mode",
            "proposed_slot_id",
        ]
        self.load()
        logging.info(f"Initialized PatientWaitlistManager with {len(self.patients)} patients")

    def load(self):
        """Load patients from the CSV file."""
        try:
            # Use the decryption helper
            loaded_patients_data = load_decrypted_csv(self.waitlist_file, self.fieldnames)
            
            self.patients = [] # Reset before populating
            for row in loaded_patients_data:
                # Handle JSON fields (availability) AFTER decryption
                if "availability" in row and isinstance(row["availability"], str) and row["availability"]:
                    try:
                        row["availability"] = json.loads(row["availability"])
                    except json.JSONDecodeError:
                        logging.warning(f"Could not parse availability JSON for patient {row.get('id')}: {row['availability']}")
                        row["availability"] = {} # Default to empty dict on error
                elif not isinstance(row.get("availability"), dict): # Ensure it's a dict if not a parsable string
                    row["availability"] = {}

                # Handle timestamp AFTER decryption
                if "timestamp" in row and isinstance(row["timestamp"], str) and row["timestamp"]:
                    try:
                        row["timestamp"] = datetime.fromisoformat(row["timestamp"])
                    except ValueError:
                        logging.warning(f"Could not parse timestamp for patient {row.get('id')}: {row['timestamp']}")
                        row["timestamp"] = datetime.now() # Default to now on error
                elif not isinstance(row.get("timestamp"), datetime): # Ensure it is datetime
                    row["timestamp"] = datetime.now()

                self.patients.append(row)
                logging.debug(f"Loaded patient: {row}")
            
            logging.info(f"Loaded and processed {len(self.patients)} patients from {self.waitlist_file}")
        except Exception as e:
            logging.error(f"Error loading or decrypting patients: {e}", exc_info=True)
            self.patients = []

    def update(self):
        """Save the current patients to the CSV file."""
        try:
            # Prepare data for CSV (convert dicts/datetimes to strings) BEFORE encryption
            patients_to_save = []
            for patient in self.patients:
                row_data = patient.copy()

                # Convert timestamp to string
                if isinstance(row_data.get("timestamp"), datetime):
                    row_data["timestamp"] = row_data["timestamp"].isoformat()

                # Convert availability to JSON string
                if isinstance(row_data.get("availability"), dict):
                    row_data["availability"] = json.dumps(row_data["availability"])
                
                patients_to_save.append(row_data)

            # Use the encryption helper
            save_encrypted_csv(patients_to_save, self.waitlist_file, self.fieldnames)
            logging.info(
                f"Updated {len(self.patients)} patients to {self.waitlist_file}"
            )
            return True
        except Exception as e:
            logging.error(f"Error updating or encrypting patients: {e}", exc_info=True)
            return False

    def get_all_patients(self):
        """Return all patients."""
        logging.info(f"Returning {len(self.patients)} patients")
        return self.patients

    def get_patient(self, patient_id):
        """Return a specific patient by ID.

        Args:
            patient_id (str): The ID of the patient to retrieve

        Returns:
            dict: The patient record if found, None otherwise
        """
        patient = next((p for p in self.patients if p.get("id") == patient_id), None)
        if patient:
            logging.info(f"Found patient {patient_id}: {patient}")
        else:
            logging.warning(f"Patient {patient_id} not found")
        return patient

    def save_backup(self):
        """Manually create a backup of the waitlist."""
        return self.update()

    def add_patient(
        self,
        name,
        phone,
        email,
        reason,
        urgency,
        appointment_type,
        duration,
        provider,
        timestamp=None,
        availability=None,
        availability_mode="available",
        **p_data
    ):
        """Add a new patient to the waitlist."""
        # Generate a unique ID
        patient_id = str(uuid.uuid4())

        # Create timestamp if not provided
        timestamp = timestamp or datetime.now()

        # Create a new patient record
        patient = {
            "id": patient_id,
            "name": name,
            "phone": phone,
            "email": email or "",
            "reason": reason or "",
            "urgency": urgency or "medium",
            "appointment_type": appointment_type or "custom",
            "duration": duration or "30",
            "provider": provider or "no preference",
            "status": "waiting",
            "timestamp": timestamp,
            "wait_time": "Just added",
            "availability": availability or {},
            "availability_mode": availability_mode or "available",
            "proposed_slot_id": "",
        }

        # Add to the list
        self.patients.append(patient)

        # Save to file
        self.update()

        return patient_id

    def remove_patient(self, patient_id):
        """Remove a patient from the waitlist by ID."""
        logging.debug(f"Attempting to remove patient with ID: {patient_id}")
        if not self.patients:
             logging.warning("Patient list is empty, cannot remove.")
             return False

        initial_count = len(self.patients)
        logging.debug(f"Initial patient count: {initial_count}")
        # Log the IDs currently in the list for comparison
        current_ids = [p.get("id", "MISSING_ID") for p in self.patients]
        logging.debug(f"Current patient IDs in list: {current_ids}")

        # Perform the filtering
        original_patients = self.patients # Keep a reference for logging if needed
        self.patients = [p for p in self.patients if p.get("id") != patient_id]

        new_count = len(self.patients)
        logging.debug(f"Patient count after filtering: {new_count}")

        if new_count < initial_count:
            logging.info(f"Patient {patient_id} found and filtered. Attempting update.")
            if self.update():
                 logging.info(f"Successfully removed patient {patient_id} and updated file.")
                 return True
            else:
                 logging.error(f"Removed patient {patient_id} from memory list, but FAILED to update file.")
                 # Restore the original list in memory since the file update failed
                 self.patients = original_patients
                 return False
        else:
            logging.warning(f"Could not remove patient {patient_id}. ID not found in the current list.")
            return False

    def update_patient(
        self,
        patient_id,
        name,
        phone,
        email,
        reason,
        urgency,
        appointment_type,
        duration,
        provider,
        availability=None,
        availability_mode="available",
    ):
        """Update an existing patient's details."""
        # Find the patient by ID
        patient_index = None
        for i, patient in enumerate(self.patients):
            if patient.get("id") == patient_id:
                patient_index = i
                break

        if patient_index is None:
            logging.warning(f"Could not update patient {patient_id}, ID not found.")
            return False  # Patient not found

        # Update the patient's details
        self.patients[patient_index].update(
            {
                "name": name,
                "phone": phone,
                "email": email,
                "reason": reason,
                "urgency": urgency,
                "appointment_type": appointment_type,
                "duration": duration,
                "provider": provider,
                "availability": availability or {},
                "availability_mode": availability_mode,
            }
        )
        logging.info(f"Updated patient {patient_id} details.")
        # Save to file
        self.update()

        return True

    def mark_as_pending(self, patient_id, slot_id):
        """Mark a patient as pending confirmation for a specific slot."""
        patient_index = -1
        for i, patient in enumerate(self.patients):
            if patient.get("id") == patient_id:
                patient_index = i
                break

        if patient_index == -1:
            logging.warning(f"Cannot mark patient {patient_id} as pending. Patient not found.")
            return False
        if self.patients[patient_index].get("status") != "waiting":
             logging.warning(f"Cannot mark patient {patient_id} as pending. Status is not 'waiting' (current: {self.patients[patient_index].get('status')}).")
             return False

        self.patients[patient_index]["status"] = "pending"
        self.patients[patient_index]["proposed_slot_id"] = slot_id
        self.update()
        logging.info(f"Marked patient {patient_id} as pending for slot {slot_id}")
        return True

    def cancel_proposal(self, patient_id):
        """Reset a pending patient back to waiting."""
        patient_index = -1
        for i, patient in enumerate(self.patients):
            if patient.get("id") == patient_id:
                patient_index = i
                break

        if patient_index == -1:
            logging.warning(f"Cannot cancel proposal for patient {patient_id}. Patient not found.")
            return False
        # Only cancel if currently pending for robustness
        if self.patients[patient_index].get("status") == "pending":
            self.patients[patient_index]["status"] = "waiting"
            self.patients[patient_index]["proposed_slot_id"] = ""
            self.update()
            logging.info(f"Cancelled proposal for patient {patient_id}. Status reset to waiting.")
            return True
        else:
             logging.warning(f"Cannot cancel proposal for patient {patient_id}. Status is not 'pending' (current: {self.patients[patient_index].get('status')}).")
             # Return False as no change was made, but it's not necessarily an error if state was already reverted.
             return False # Or True depending on desired behaviour if already waiting

    def mark_as_scheduled(self, patient_id):
        """Mark a patient as scheduled (alternative to removal)."""
        patient_index = -1
        for i, patient in enumerate(self.patients):
            if patient.get("id") == patient_id:
                patient_index = i
                break

        if patient_index == -1:
            logging.warning(f"Cannot mark patient {patient_id} as scheduled. Patient not found.")
            return False

        # Optionally check if status was 'pending' before marking scheduled
        # if self.patients[patient_index].get("status") != "pending":
        #    logging.warning(f"Marking patient {patient_id} as scheduled, but status wasn't pending (current: {self.patients[patient_index].get('status')}).")

        self.patients[patient_index]["status"] = "scheduled"
        # Consider clearing proposed_slot_id here as well?
        # self.patients[patient_index]["proposed_slot_id"] = ""
        self.update()
        logging.info(f"Marked patient {patient_id} as scheduled.")
        return True

    def update_wait_times(self):
        """Update wait times for all patients based on their timestamp."""
        now = datetime.now()
        changed = False
        for patient in self.patients:
            if patient.get("status") == "waiting":
                timestamp = patient.get("timestamp")
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp)
                        patient["timestamp"] = timestamp
                    except ValueError:
                        logging.warning(f"Could not parse timestamp string '{timestamp}' for patient {patient.get('id')}. Using current time.")
                        timestamp = now
                        patient["timestamp"] = timestamp

                elif not isinstance(timestamp, datetime):
                     logging.warning(f"Invalid timestamp type '{type(timestamp)}' for patient {patient.get('id')}. Using current time.")
                     timestamp = now
                     patient["timestamp"] = timestamp

                time_diff = now - timestamp
                days = time_diff.days

                # Calculate wait time string as just days
                new_wait_time = f"{days} days"

                if patient.get("wait_time") != new_wait_time:
                    patient["wait_time"] = new_wait_time
                    changed = True

        if changed:
            self.update()
            logging.debug("Wait times updated.")
        return True


class ProviderManager:
    """Manages provider information, persisting to CSV files."""

    def __init__(self, provider_file="provider.csv"):
        """Initialize with file paths."""
        self.provider_file = provider_file
        self.providers = []
        self.headers = ["name"]
        self.load()

    def load(self):
        """Load providers from the CSV file."""
        try:
            # Use the decryption helper
            self.providers = load_decrypted_csv(self.provider_file, self.headers)
            logging.info(
                f"Loaded {len(self.providers)} providers from {self.provider_file}"
            )
        except Exception as e:
            logging.error(f"Error loading or decrypting providers: {e}", exc_info=True)
            self.providers = []

    def update(self):
        """Save the current providers to the CSV file."""
        try:
            # Use the encryption helper
            save_encrypted_csv(self.providers, self.provider_file, self.headers)
            logging.info(
                f"Updated {len(self.providers)} providers to {self.provider_file}"
            )
            return True
        except Exception as e:
            logging.error(f"Error updating or encrypting providers: {e}", exc_info=True)
            return False

    def get_provider_list(self):
        """Return all providers."""
        return self.providers

    def add_provider(self, first_name, last_initial=None):
        """Add a provider to the list."""
        if not first_name:
            return False

        # Format the provider name
        provider_name = first_name.strip()
        if last_initial and last_initial.strip():
            provider_name += f" {last_initial.strip()}"

        # Check if provider already exists
        for provider in self.providers:
            if provider.get("name", "").lower() == provider_name.lower():
                return False  # Provider already exists

        # Add the provider
        self.providers.append({"name": provider_name})
        self.update()
        return True

    def remove_provider(self, first_name, last_initial=None):
        """Remove a provider from the list."""
        if not first_name:
            return False

        # Format the provider name
        provider_name = first_name.strip()
        if last_initial and last_initial.strip():
            provider_name += f" {last_initial.strip()}"

        # Find and remove the provider
        initial_count = len(self.providers)
        self.providers = [
            p
            for p in self.providers
            if p.get("name", "").lower() != provider_name.lower()
        ]

        if len(self.providers) < initial_count:
            self.update()
            return True
        return False
