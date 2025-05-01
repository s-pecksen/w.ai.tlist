import os
import csv
import json
from datetime import datetime
import logging
from typing import List, Dict, Any, Optional
import uuid


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
            "matched_patient_id",
            "matched_patient_name",
            "proposed_patient_id",
            "proposed_patient_name",
        ]
        self.load()

    def load(self):
        """Load slots from the CSV file."""
        self.slots = []
        if os.path.exists(self.slots_file):
            try:
                with open(
                    self.slots_file, "r", newline="", encoding="utf-8"
                ) as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        self.slots.append(row)
                logging.info(f"Loaded {len(self.slots)} slots from {self.slots_file}")
            except Exception as e:
                logging.error(f"Error loading slots: {e}", exc_info=True)
                self.slots = []
        else:
            logging.info(
                f"No slots file found at {self.slots_file}. Starting with empty list."
            )

    def update(self):
        """Save the current slots to the CSV file."""
        try:
            # Write current data
            with open(self.slots_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.headers)
                writer.writeheader()
                for slot in self.slots:
                    writer.writerow({k: slot.get(k, "") for k in self.headers})
            logging.info(f"Updated {len(self.slots)} slots to {self.slots_file}")
            return True
        except Exception as e:
            logging.error(f"Error updating slots: {e}", exc_info=True)
            return False

    def get_all_slots(self):
        """Return all slots."""
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
            "matched_patient_id": "",
            "matched_patient_name": "",
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
            }
        )

        # Save to file
        self.update()

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

    def load(self):
        """Load patients from the CSV file."""
        self.patients = []
        if os.path.exists(self.waitlist_file):
            try:
                with open(
                    self.waitlist_file, "r", newline="", encoding="utf-8"
                ) as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        # Handle JSON fields
                        if "availability" in row and row["availability"]:
                            try:
                                row["availability"] = json.loads(row["availability"])
                            except json.JSONDecodeError:
                                row["availability"] = {}
                        else:
                            row["availability"] = {}

                        # Handle timestamp
                        if "timestamp" in row and row["timestamp"]:
                            try:
                                row["timestamp"] = datetime.fromisoformat(
                                    row["timestamp"]
                                )
                            except ValueError:
                                row["timestamp"] = datetime.now()
                        else:
                            row["timestamp"] = datetime.now()

                        self.patients.append(row)
                logging.info(
                    f"Loaded {len(self.patients)} patients from {self.waitlist_file}"
                )
            except Exception as e:
                logging.error(f"Error loading patients: {e}", exc_info=True)
                self.patients = []
        else:
            logging.info(
                f"No waitlist file found at {self.waitlist_file}. Starting with empty list."
            )

    def update(self):
        """Save the current patients to the CSV file."""
        try:
            # Write current data
            with open(self.waitlist_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
                writer.writeheader()
                for patient in self.patients:
                    row_data = patient.copy()

                    # Convert timestamp to string
                    if isinstance(row_data.get("timestamp"), datetime):
                        row_data["timestamp"] = row_data["timestamp"].isoformat()

                    # Convert availability to JSON string
                    if isinstance(row_data.get("availability"), dict):
                        row_data["availability"] = json.dumps(row_data["availability"])

                    writer.writerow({k: row_data.get(k, "") for k in self.fieldnames})
            logging.info(
                f"Updated {len(self.patients)} patients to {self.waitlist_file}"
            )
            return True
        except Exception as e:
            logging.error(f"Error updating patients: {e}", exc_info=True)
            return False

    def get_all_patients(self):
        """Return all patients."""
        return self.patients

    def get_patient(self, patient_id):
        """Return a specific patient by ID.

        Args:
            patient_id (str): The ID of the patient to retrieve

        Returns:
            dict: The patient record if found, None otherwise
        """
        for patient in self.patients:
            if patient.get("id") == patient_id:
                return patient
        return None

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
        availability=None,
        availability_mode="available",
    ):
        """Add a new patient to the waitlist."""
        # Generate a unique ID
        patient_id = str(uuid.uuid4())

        # Create timestamp
        timestamp = datetime.now()

        # Create a new patient record
        patient = {
            "id": patient_id,
            "name": name,
            "phone": phone,
            "email": email,
            "reason": reason,
            "urgency": urgency,
            "appointment_type": appointment_type,
            "duration": duration,
            "provider": provider,
            "status": "waiting",
            "timestamp": timestamp,
            "wait_time": "Just added",
            "availability": availability or {},
            "availability_mode": availability_mode,
            "proposed_slot_id": "",
        }

        # Add to the list
        self.patients.append(patient)

        # Save to file
        self.update()

        return patient_id

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

        # Save to file
        self.update()

        return True

    def update_wait_times(self):
        """Update wait times for all patients based on their timestamp."""
        now = datetime.now()
        for patient in self.patients:
            if patient.get("status") == "waiting":
                timestamp = patient.get("timestamp")
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.fromisoformat(timestamp)
                    except ValueError:
                        timestamp = now

                if isinstance(timestamp, datetime):
                    # Calculate time difference
                    time_diff = now - timestamp

                    # Format the wait time
                    days = time_diff.days
                    hours, remainder = divmod(time_diff.seconds, 3600)
                    minutes, _ = divmod(remainder, 60)

                    wait_time = ""
                    if days > 0:
                        wait_time += f"{days} days"
                        if hours > 0 or minutes > 0:
                            wait_time += ", "

                    if hours > 0:
                        wait_time += f"{hours} hours"
                        if minutes > 0:
                            wait_time += ", "

                    if minutes > 0 or (days == 0 and hours == 0):
                        wait_time += f"{minutes} minutes"

                    patient["wait_time"] = wait_time

        # Save the updated wait times
        self.update()
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
            if os.path.exists(self.provider_file):
                with open(
                    self.provider_file, "r", newline="", encoding="utf-8"
                ) as csvfile:
                    reader = csv.DictReader(csvfile)
                    self.providers = list(reader)
                logging.info(
                    f"Loaded {len(self.providers)} providers from {self.provider_file}"
                )
            else:
                logging.info(
                    f"Provider file {self.provider_file} not found, starting with empty list"
                )
                self.providers = []
        except Exception as e:
            logging.error(f"Error loading providers: {e}", exc_info=True)
            self.providers = []

    def update(self):
        """Save the current providers to the CSV file."""
        try:
            # Write current data
            with open(self.provider_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.headers)
                writer.writeheader()
                for provider in self.providers:
                    writer.writerow({k: provider.get(k, "") for k in self.headers})
            logging.info(
                f"Updated {len(self.providers)} providers to {self.provider_file}"
            )
            return True
        except Exception as e:
            logging.error(f"Error updating providers: {e}", exc_info=True)
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
