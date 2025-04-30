import os
import csv
import json
import datetime
from typing import List, Dict, Any, Optional
import uuid
import logging  # Use logging instead of print


class PatientWaitlistManager:
    def __init__(self):
        """
        Initialize the Patient Waitlist Manager.
        """
        # Define fieldnames early, including availability, mode, and proposed slot
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
            "availability",  # Stores JSON of day/time prefs
            "availability_mode",  # Stores 'available' or 'unavailable'
            "proposed_slot_id",  # Stores the ID of the slot proposed to the patient
        ]
        # Define valid statuses
        self.valid_statuses = ["waiting", "scheduled", "awaiting confirmation"]

        # Start with an empty list
        self.patients = []
        logging.info("Starting with empty patient list.")

    def add_patient(
        self,
        name: str,
        phone: str,
        email: str = "",
        reason: str = "",
        urgency: str = "medium",
        appointment_type: str = "consultation",
        duration: str = "30",
        provider: str = "no preference",
        availability: Optional[Dict[str, List[str]]] = None,
        availability_mode: str = "available",  # Added parameter
        timestamp: Optional[datetime.datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        """Adds a new patient with structured availability and mode."""
        try:
            patient_id = str(uuid.uuid4())
            entry_timestamp = timestamp if timestamp else datetime.datetime.now()
            patient_availability = availability if availability is not None else {}
            mode = availability_mode.lower() if availability_mode else "available"
            valid_mode = mode if mode in ["available", "unavailable"] else "available"

            patient = {
                "id": patient_id,
                "name": name,
                "phone": phone,
                "email": email,
                "reason": reason,
                "urgency": urgency,
                "appointment_type": appointment_type,
                "duration": str(duration),
                "provider": provider,
                "status": "waiting",  # New patients start as waiting
                "timestamp": entry_timestamp,
                "wait_time": "0 minutes",
                "availability": patient_availability,
                "availability_mode": valid_mode,
                "proposed_slot_id": "",  # Initialize as empty
            }
            self.patients.append(patient)
            logging.info(f"Added patient {patient_id} ({name}).")
            return patient
        except Exception as e:
            logging.error(f"Error adding patient: {e}", exc_info=True)
            return None

    def get_all_patients(
        self, status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get patients, optionally filtering by status."""
        if status_filter:
            status_filter_lower = status_filter.lower()
            if status_filter_lower not in self.valid_statuses:
                logging.warning(
                    f"Invalid status filter '{status_filter}'. Returning all patients."
                )
                return self.patients
            return [
                p
                for p in self.patients
                if p.get("status", "").lower() == status_filter_lower
            ]
        return self.patients

    def update_wait_times(self):
        """Update wait time for all non-scheduled patients."""
        now = datetime.datetime.now()
        updated = False
        for patient in self.patients:
            # Update for waiting and awaiting confirmation
            if patient.get("status") in [
                "waiting",
                "awaiting confirmation",
            ] and isinstance(patient.get("timestamp"), datetime.datetime):
                delta = now - patient["timestamp"]
                days = delta.days
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, _ = divmod(remainder, 60)

                # Build wait time string (e.g., "5 days, 3 hours" or "1 hour, 30 minutes")
                wait_parts = []
                if days > 0:
                    wait_parts.append(f"{days} day{'s' if days != 1 else ''}")
                if hours > 0:
                    wait_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
                if (
                    not wait_parts and minutes >= 0
                ):  # Show minutes if less than an hour wait
                    wait_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

                new_wait_time = ", ".join(wait_parts) if wait_parts else "0 minutes"

                if patient.get("wait_time") != new_wait_time:
                    patient["wait_time"] = new_wait_time
                    updated = True
            elif patient.get("status") == "scheduled":
                # Clear wait time for scheduled patients
                if patient.get("wait_time") != "":
                    patient["wait_time"] = ""
                    updated = True

    def update_patient_status(
        self, patient_id: str, new_status: str, proposed_slot_id: Optional[str] = None
    ) -> bool:
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
            logging.error(
                f"Attempted to set invalid status '{new_status}' for patient {patient_id}."
            )
            return False

        patient_found = False
        for i, patient in enumerate(self.patients):
            if patient.get("id") == patient_id:
                # Update status
                self.patients[i]["status"] = new_status_lower

                # Update proposed_slot_id based on status
                if new_status_lower == "awaiting confirmation":
                    self.patients[i]["proposed_slot_id"] = (
                        proposed_slot_id if proposed_slot_id else ""
                    )
                    logging.debug(
                        f"Set patient {patient_id} status to 'awaiting confirmation' for slot {proposed_slot_id}"
                    )
                else:
                    # Clear proposed slot ID if status is not awaiting confirmation
                    if self.patients[i].get("proposed_slot_id"):
                        logging.debug(
                            f"Clearing proposed slot ID for patient {patient_id} due to status change to '{new_status_lower}'"
                        )
                    self.patients[i]["proposed_slot_id"] = ""

                # Clear wait time if scheduled
                if new_status_lower == "scheduled":
                    self.patients[i]["wait_time"] = ""

                patient_found = True
                break  # Exit loop once patient is found

        if patient_found:
            logging.info(
                f"Updated patient {patient_id} status to '{new_status_lower}'."
            )
        else:
            logging.warning(
                f"Could not update status for patient {patient_id}: Patient not found."
            )

        return patient_found

    # Keep schedule_patient and remove_patient simple, status changes handled by update_patient_status
    def schedule_patient(self, patient_id: str) -> bool:
        """Mark a patient as scheduled (uses update_patient_status)."""
        return self.update_patient_status(patient_id, "scheduled")

    def remove_patient(self, patient_id: str) -> bool:
        """Remove a patient."""
        initial_len = len(self.patients)
        self.patients = [p for p in self.patients if p.get("id") != patient_id]
        if len(self.patients) < initial_len:
            logging.info(f"Removed patient {patient_id}.")
            return True
        logging.warning(f"Attempted to remove non-existent patient ID: {patient_id}")
        return False

    def find_eligible_patients(
        self,
        provider_name: str,
        slot_duration: str,
        slot_day_of_week: Optional[str] = None,
        slot_period: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
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
        for patient in self.get_all_patients(status_filter="waiting"):
            # 1. Check Duration
            if str(patient.get("duration", "0")) != slot_duration_str:
                continue

            # 2. Check Provider Preference
            patient_provider = patient.get("provider", "").strip().lower()
            is_provider_match = patient_provider == provider_name_lower
            is_no_preference = (
                patient_provider == "no preference" or not patient_provider
            )
            if not (is_provider_match or is_no_preference):
                continue

            # 3. Check Day and Time Availability (with Mode Logic)
            patient_availability_prefs = patient.get("availability", {})
            patient_mode = patient.get("availability_mode", "available")
            is_available_for_slot = True

            if slot_day_lower and slot_period_upper:
                has_preferences = bool(patient_availability_prefs)
                slot_matches_preference = False
                # Find matching day key case-insensitively
                matching_day_key = next(
                    (
                        k
                        for k in patient_availability_prefs
                        if k.lower() == slot_day_lower
                    ),
                    None,
                )

                if matching_day_key:
                    day_prefs = patient_availability_prefs.get(matching_day_key, [])
                    day_prefs_upper = [str(p).strip().upper() for p in day_prefs]
                    if slot_period_upper in day_prefs_upper:
                        slot_matches_preference = True

                if patient_mode == "available":
                    if has_preferences and not slot_matches_preference:
                        is_available_for_slot = False
                elif patient_mode == "unavailable":
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
        urgency_order = {"high": 0, "medium": 1, "low": 2}
        emergency_str = "emergency_exam"
        eligible_patients.sort(
            key=lambda p: (
                (
                    0
                    if p.get("appointment_type", "").strip().lower() == emergency_str
                    else 1
                ),  # Emergency first
                urgency_order.get(
                    p.get("urgency", "medium").strip().lower(), 1
                ),  # Then urgency
                p.get(
                    "timestamp", datetime.datetime.max
                ),  # Then timestamp (earlier first)
            )
        )

        return eligible_patients

    def get_patient_by_id(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Finds a patient by their unique ID."""
        for patient in self.patients:
            if patient.get("id") == patient_id:
                return patient
        return None

    def update_patient(self, patient_id: str, updated_data: Dict[str, Any]) -> bool:
        """
        Updates an existing patient's editable data fields. Status is handled separately.
        """
        patient_found = False
        for i, patient in enumerate(self.patients):
            if patient.get("id") == patient_id:
                # Update only editable fields from the form
                self.patients[i]["name"] = updated_data.get("name", patient.get("name"))
                self.patients[i]["phone"] = updated_data.get(
                    "phone", patient.get("phone")
                )
                self.patients[i]["email"] = updated_data.get(
                    "email", patient.get("email")
                )
                self.patients[i]["reason"] = updated_data.get(
                    "reason", patient.get("reason")
                )
                self.patients[i]["urgency"] = updated_data.get(
                    "urgency", patient.get("urgency")
                )
                self.patients[i]["appointment_type"] = updated_data.get(
                    "appointment_type", patient.get("appointment_type")
                )
                self.patients[i]["duration"] = str(
                    updated_data.get("duration", patient.get("duration"))
                )
                self.patients[i]["provider"] = updated_data.get(
                    "provider", patient.get("provider")
                )

                # Handle availability update
                availability = updated_data.get("availability")
                self.patients[i]["availability"] = (
                    availability
                    if isinstance(availability, dict)
                    else patient.get("availability", {})
                )

                # Handle availability mode update
                mode = updated_data.get(
                    "availability_mode", patient.get("availability_mode", "available")
                ).lower()
                self.patients[i]["availability_mode"] = (
                    mode if mode in ["available", "unavailable"] else "available"
                )

                # Do NOT update status, timestamp, wait_time, or proposed_slot_id here
                patient_found = True
                logging.info(f"Updated editable details for patient {patient_id}.")
                break  # Exit loop once patient is found and updated

        if not patient_found:
            logging.warning(
                f"Could not update patient details for {patient_id}: Patient not found."
            )

        return patient_found
