import os
import csv
import uuid
from datetime import datetime, date
import logging
from typing import Optional, Dict, Any, List


class CancelledSlotManager:
    """Manages cancelled appointment slots, persisting them to CSV files."""

    def __init__(self):
        self.slots = []  # In-memory list of slot dictionaries
        # Added proposed_patient_id and proposed_patient_name
        self.headers = [
            "id",
            "provider",
            "duration",
            "slot_date",
            "slot_period",
            "slot_time",
            "notes",
            "matched_patient_id",
            "matched_patient_name",  # Final match
            "proposed_patient_id",
            "proposed_patient_name",  # Intermediate proposal
        ]

        self._load_slots()
        logging.info(
            f"CancelledSlotManager initialized. Loaded {len(self.slots)} slots."
        )

    def _load_slots(self, slots_file):
        """Loads slots from the CSV file."""
        if os.path.exists(slots_file):
            try:
                with open(slots_file, "r", newline="", encoding="utf-8") as csvfile:
                    reader = csv.DictReader(csvfile)
                    headers = reader.fieldnames or []
                    # Core required headers
                    required_headers = [
                        "id",
                        "provider",
                        "duration",
                        "slot_date",
                        "slot_period",
                    ]
                    if not all(h in headers for h in required_headers):
                        logging.warning(
                            f"Header mismatch or missing essential headers {required_headers} in {self.slots_file}. Got {headers}. Attempting load anyway."
                        )
                        if "id" not in headers:
                            logging.error(
                                "Critical header 'id' missing. Cannot load slots."
                            )
                            self.slots = []
                            return

                    loaded_slots = []
                    # Check for optional/newer columns
                    has_time_col = "slot_time" in headers
                    has_proposed_id_col = "proposed_patient_id" in headers
                    has_proposed_name_col = "proposed_patient_name" in headers

                    for row in reader:
                        # Matched patient (final assignment)
                        matched_patient = None
                        if row.get("matched_patient_id") and row.get(
                            "matched_patient_name"
                        ):
                            matched_patient = {
                                "id": row.get("matched_patient_id"),
                                "name": row.get("matched_patient_name"),
                            }

                        # Date/Day parsing (no change)
                        slot_date_obj = None
                        slot_day_of_week = None
                        slot_date_str = row.get("slot_date")
                        if slot_date_str:
                            try:
                                slot_date_obj = date.fromisoformat(slot_date_str)
                                slot_day_of_week = slot_date_obj.strftime("%A")
                            except ValueError:
                                logging.warning(
                                    f"Could not parse slot_date '{slot_date_str}' for slot ID {row.get('id')}."
                                )

                        # Period/Time parsing (no change)
                        slot_period_raw = row.get("slot_period", "").strip().upper()
                        slot_period = (
                            slot_period_raw if slot_period_raw in ["AM", "PM"] else None
                        )
                        slot_time = row.get("slot_time", "") if has_time_col else ""

                        # Proposed patient (intermediate step)
                        proposed_patient_id = (
                            row.get("proposed_patient_id", "")
                            if has_proposed_id_col
                            else ""
                        )
                        proposed_patient_name = (
                            row.get("proposed_patient_name", "")
                            if has_proposed_name_col
                            else ""
                        )

                        # Build the slot dictionary
                        slot = {
                            "id": row.get("id"),
                            "provider": row.get("provider"),
                            "duration": row.get("duration"),
                            "slot_date": slot_date_obj,
                            "slot_day_of_week": slot_day_of_week,
                            "slot_period": slot_period,
                            "slot_time": slot_time,
                            "notes": row.get("notes", ""),
                            "matched_patient": matched_patient,
                            "proposed_patient_id": proposed_patient_id,
                            "proposed_patient_name": proposed_patient_name,
                        }
                        # Basic validation
                        if all(
                            slot.get(k)
                            for k in [
                                "id",
                                "provider",
                                "duration",
                                "slot_date",
                                "slot_period",
                            ]
                        ):
                            loaded_slots.append(slot)
                        else:
                            logging.warning(
                                f"Skipping row due to missing essential data (ID, Provider, Duration, Date, Period): {row}"
                            )

                    self.slots = loaded_slots
                    logging.info(
                        f"Successfully loaded {len(self.slots)} slots from {self.slots_file}"
                    )

            except FileNotFoundError:
                logging.warning(
                    f"Slots file {self.slots_file} not found during load attempt."
                )
                self.slots = []
            except Exception as e:
                logging.error(
                    f"Error loading cancelled slots from {self.slots_file}: {e}",
                    exc_info=True,
                )
                self.slots = []
        else:
            logging.info(
                "No existing cancelled slots file found. Starting with an empty list."
            )
            self.slots = []

    def _save_slots(self):
        """Saves the current list of slots to the CSV file."""
        try:
            with open(self.slots_file, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(
                    csvfile, fieldnames=self.headers, extrasaction="ignore"
                )
                writer.writeheader()
                for slot in self.slots:
                    row_data = slot.copy()  # Start with a copy

                    # Format date
                    if isinstance(row_data.get("slot_date"), date):
                        row_data["slot_date"] = row_data["slot_date"].isoformat()
                    else:
                        row_data["slot_date"] = ""

                    # Flatten matched patient
                    matched = row_data.pop("matched_patient", None)
                    row_data["matched_patient_id"] = (
                        matched.get("id", "") if matched else ""
                    )
                    row_data["matched_patient_name"] = (
                        matched.get("name", "") if matched else ""
                    )

                    # Ensure proposed fields exist (even if empty)
                    row_data.setdefault("proposed_patient_id", "")
                    row_data.setdefault("proposed_patient_name", "")

                    # Write only headers defined in self.headers
                    writer.writerow({k: row_data.get(k, "") for k in self.headers})

            logging.info(
                f"Successfully saved {len(self.slots)} slots to {self.slots_file}"
            )
        except Exception as e:
            logging.error(
                f"Error saving cancelled slots to {self.slots_file}: {e}", exc_info=True
            )

    def add_slot(
        self,
        provider: str,
        duration: str,
        slot_date: date,
        slot_period: str,
        slot_time: str,
        notes: str = "",
    ):
        """Adds a new cancelled slot and saves."""
        new_id = str(uuid.uuid4())
        day_of_week = slot_date.strftime("%A") if isinstance(slot_date, date) else None
        period_upper = slot_period.strip().upper() if slot_period else None
        if period_upper not in ["AM", "PM"]:
            logging.error(f"Invalid slot_period '{slot_period}'.")
            return None
        if not slot_time:
            logging.error("slot_time cannot be empty.")
            return None

        new_slot = {
            "id": new_id,
            "provider": provider,
            "duration": str(duration),
            "slot_date": slot_date,
            "slot_day_of_week": day_of_week,
            "slot_period": period_upper,
            "slot_time": slot_time,
            "notes": notes,
            "matched_patient": None,
            "proposed_patient_id": "",  # Initialize proposal fields
            "proposed_patient_name": "",
        }
        self.slots.append(new_slot)
        self._save_slots()
        logging.debug(
            f"Added slot {new_id} for {slot_date} ({day_of_week} {period_upper} at {slot_time})."
        )
        return new_slot

    def remove_slot(self, appointment_id: str) -> bool:
        """Removes a slot ONLY if it is not matched or proposed."""
        slot_to_remove = self.get_slot_by_id(appointment_id)
        if not slot_to_remove:
            logging.warning(
                f"Attempted to remove non-existent slot ID: {appointment_id}"
            )
            return False
        # Prevent removal if matched or proposed
        if slot_to_remove.get("matched_patient"):
            logging.warning(
                f"Attempted to remove already matched slot ID: {appointment_id}"
            )
            return False
        if slot_to_remove.get("proposed_patient_id"):
            logging.warning(
                f"Attempted to remove a proposed slot ID: {appointment_id}. Please un-propose first."
            )
            return False

        initial_length = len(self.slots)
        self.slots = [slot for slot in self.slots if slot.get("id") != appointment_id]
        if len(self.slots) < initial_length:
            self._save_slots()
            logging.info(f"Removed slot {appointment_id}.")
            return True
        return False  # Should not happen if checks above pass

    def update_slot(
        self,
        appointment_id: str,
        provider: str,
        duration: str,
        slot_date: date,
        slot_period: str,
        slot_time: str,
        notes: str,
    ):
        """Updates details of an existing slot ONLY if not matched or proposed."""
        day_of_week = slot_date.strftime("%A") if isinstance(slot_date, date) else None
        period_upper = slot_period.strip().upper() if slot_period else None
        if period_upper not in ["AM", "PM"]:
            logging.error(f"Invalid slot_period '{slot_period}'.")
            return False
        if not slot_time:
            logging.error("slot_time cannot be empty.")
            return False

        updated = False
        for i, slot in enumerate(self.slots):
            if slot.get("id") == appointment_id:
                # Prevent updating matched or proposed slots
                if slot.get("matched_patient"):
                    logging.warning(
                        f"Attempted to update already matched slot {appointment_id}."
                    )
                    return False
                if slot.get("proposed_patient_id"):
                    logging.warning(
                        f"Attempted to update a proposed slot {appointment_id}."
                    )
                    return False

                self.slots[i].update(
                    {
                        "provider": provider,
                        "duration": str(duration),
                        "slot_date": slot_date,
                        "slot_day_of_week": day_of_week,
                        "slot_period": period_upper,
                        "slot_time": slot_time,
                        "notes": notes,
                    }
                )
                updated = True
                break
        if updated:
            self._save_slots()
            logging.info(
                f"Updated slot {appointment_id} to {slot_date} ({day_of_week} {period_upper} at {slot_time})."
            )
        else:
            logging.warning(
                f"Attempted to update non-existent slot ID: {appointment_id}"
            )
        return updated

    def assign_patient_to_slot(
        self, appointment_id: str, patient_data: Dict[str, Any]
    ) -> bool:
        """Marks a slot as finally matched with a patient and saves."""
        assigned = False
        for i, slot in enumerate(self.slots):
            if slot.get("id") == appointment_id:
                # Clear proposal info when final assignment happens
                self.slots[i]["proposed_patient_id"] = ""
                self.slots[i]["proposed_patient_name"] = ""
                # Set matched info
                self.slots[i]["matched_patient"] = {
                    "id": patient_data.get("id"),
                    "name": patient_data.get("name"),
                }
                assigned = True
                logging.info(
                    f"Final assignment: Patient {patient_data.get('id')} assigned to slot {appointment_id}."
                )
                break
        if assigned:
            self._save_slots()
        else:
            logging.error(f"Failed to assign patient: Slot {appointment_id} not found.")
        return assigned

    def get_slot_by_id(self, appointment_id):
        """Retrieves a single slot by its ID."""
        for slot in self.slots:
            if slot.get("id") == appointment_id:
                return slot  # Returns the dict including proposal info
        return None

    def get_all_slots(self) -> List[Dict[str, Any]]:
        """Returns a copy of the list of all slots, adding an 'is_proposed' flag."""
        all_slots_copy = []
        for slot in self.slots:
            slot_copy = slot.copy()
            # Add convenience flag for templates
            slot_copy["is_proposed"] = bool(slot_copy.get("proposed_patient_id"))
            all_slots_copy.append(slot_copy)
        return all_slots_copy

    # --- New methods for proposal ---
    def mark_slot_as_proposed(
        self, appointment_id: str, patient_id: str, patient_name: str
    ) -> bool:
        """Marks a slot as proposed to a specific patient."""
        updated = False
        for i, slot in enumerate(self.slots):
            if slot.get("id") == appointment_id:
                # Check if already matched or proposed to someone else
                if slot.get("matched_patient"):
                    logging.warning(
                        f"Cannot propose slot {appointment_id}: Already matched."
                    )
                    return False
                if (
                    slot.get("proposed_patient_id")
                    and slot.get("proposed_patient_id") != patient_id
                ):
                    logging.warning(
                        f"Cannot propose slot {appointment_id}: Already proposed to patient {slot.get('proposed_patient_id')}."
                    )
                    return False

                self.slots[i]["proposed_patient_id"] = patient_id
                self.slots[i]["proposed_patient_name"] = patient_name
                updated = True
                logging.info(
                    f"Marked slot {appointment_id} as proposed to patient {patient_id} ({patient_name})."
                )
                break
        if updated:
            self._save_slots()
        else:
            logging.warning(
                f"Could not mark slot {appointment_id} as proposed: Slot not found."
            )
        return updated

    def unmark_slot_as_proposed(self, appointment_id: str) -> bool:
        """Clears the proposed patient information from a slot."""
        updated = False
        for i, slot in enumerate(self.slots):
            if slot.get("id") == appointment_id:
                if not slot.get("proposed_patient_id"):
                    logging.warning(
                        f"Slot {appointment_id} was not marked as proposed."
                    )
                    return True  # Nothing to do, count as success

                self.slots[i]["proposed_patient_id"] = ""
                self.slots[i]["proposed_patient_name"] = ""
                updated = True
                logging.info(f"Unmarked slot {appointment_id} as proposed.")
                break
        if updated:
            self._save_slots()
        else:
            logging.warning(
                f"Could not unmark slot {appointment_id} as proposed: Slot not found."
            )
        return updated
