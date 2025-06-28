from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from src.repositories.slot_repository import SlotRepository
from src.repositories.patient_repository import PatientRepository
from src.repositories.provider_repository import ProviderRepository
from src.services.matching_service import MatchingService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

slots_bp = Blueprint('slots', __name__)
slot_repo = SlotRepository()
patient_repo = PatientRepository()
provider_repo = ProviderRepository()
matching_service = MatchingService()

@slots_bp.route("/slots", methods=["GET"])
@login_required
def slots():
    """Display slots page with available slots and matching functionality."""
    try:
        # Get all slots for the user
        all_slots = slot_repo.get_all_slots(current_user.id)
        
        # Get providers for display
        providers = provider_repo.get_providers(current_user.id)
        provider_map = provider_repo.get_provider_map(current_user.id)
        
        # Get current appointment ID from session for matching
        current_appointment_id = session.get("current_appointment_id")
        
        # If we have a current appointment, find matches
        eligible_patients = []
        ineligible_patients = []
        current_slot = None
        
        if current_appointment_id:
            current_slot = slot_repo.get_by_id(current_appointment_id)
            if current_slot:
                eligible_patients, ineligible_patients = matching_service.find_matches_for_slot(
                    current_appointment_id, current_user.id
                )
        
        # Get all waiting patients for the general list
        waiting_patients = patient_repo.get_by_status(current_user.id, "waiting")
        
        return render_template(
            "slots.html",
            slots=all_slots,
            providers=providers,
            provider_map=provider_map,
            eligible_patients=eligible_patients,
            ineligible_patients=ineligible_patients,
            waiting_patients=waiting_patients,
            current_slot=current_slot,
            current_user_name=current_user.user_name_for_message or "the scheduling team"
        )
    except Exception as e:
        logger.error(f"A critical error occurred in the slots route: {e}", exc_info=True)
        flash("A critical error occurred. Please try again.", "danger")
        return redirect(url_for('main.index'))

@slots_bp.route("/add_cancelled_appointment", methods=["POST"])
@login_required
def add_cancelled_appointment():
    """Add a new cancelled appointment (open slot)"""
    provider = request.form.get("provider")
    slot_date = request.form.get("date")
    slot_time_str = request.form.get("time")
    duration = request.form.get("duration")
    notes = request.form.get("notes", "")

    if not all([provider, slot_date, slot_time_str, duration]):
        flash("All required fields must be filled", "danger")
        return redirect(url_for("slots.slots"))

    # Determine AM/PM from time for efficient filtering
    try:
        time_obj = datetime.strptime(slot_time_str, "%H:%M").time()
        slot_period = "PM" if time_obj.hour >= 12 else "AM"
    except ValueError:
        flash("Invalid time format. Please use HH:MM.", "danger")
        return redirect(url_for("slots.slots"))
    
    try:
        # Include user_id with the insert for RLS
        slot_data = {
            "provider": provider,
            "date": slot_date,
            "time": slot_time_str,
            "duration": duration,
            "notes": notes,
            "slot_period": slot_period,
            "user_id": current_user.id
        }
        
        result = slot_repo.create(slot_data)
        if result:
            flash("Open slot added successfully", "success")
        else:
            flash("Error adding open slot.", "danger")
            
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")

    return redirect(url_for("slots.slots"))

@slots_bp.route("/remove_cancelled_slot/<appointment_id>", methods=["POST"])
@login_required
def remove_cancelled_slot(appointment_id):
    """Remove a cancelled appointment (open slot)"""
    try:
        success = slot_repo.delete(appointment_id, current_user.id)
        if success:
            flash("Open slot removed successfully", "success")
        else:
            flash("Error removing open slot. It may have already been removed.", "danger")
    except Exception as e:
        logger.error(f"Error removing slot {appointment_id}: {e}", exc_info=True)
        flash("An error occurred while removing the slot.", "danger")
    return redirect(url_for("slots.slots"))

@slots_bp.route("/update_cancelled_slot/<appointment_id>", methods=["POST"])
@login_required
def update_cancelled_slot(appointment_id):
    """Update a cancelled appointment (open slot)"""
    provider = request.form.get("provider")
    slot_date = request.form.get("date")
    slot_time_str = request.form.get("time")
    duration = request.form.get("duration")
    notes = request.form.get("notes", "")

    if not all([provider, slot_date, slot_time_str, duration]):
        flash("All required fields must be filled", "danger")
        return redirect(url_for("slots.slots"))

    # Determine AM/PM from time for efficient filtering
    try:
        time_obj = datetime.strptime(slot_time_str, "%H:%M").time()
        slot_period = "PM" if time_obj.hour >= 12 else "AM"
    except ValueError:
        flash("Invalid time format. Please use HH:MM.", "danger")
        return redirect(url_for("slots.slots"))
    
    try:
        update_data = {
            "provider": provider,
            "date": slot_date,
            "time": slot_time_str,
            "duration": duration,
            "notes": notes,
            "slot_period": slot_period
        }
        
        success = slot_repo.update(appointment_id, current_user.id, update_data)
        if success:
            flash("Open slot updated successfully", "success")
        else:
            flash("Error updating open slot.", "danger")
            
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")

    return redirect(url_for("slots.slots"))

@slots_bp.route("/find_matches_for_appointment/<appointment_id>", methods=["POST"])
@login_required
def find_matches_for_appointment(appointment_id):
    """Find matching patients for a cancelled appointment"""
    session["current_appointment_id"] = appointment_id
    return redirect(url_for("slots.slots") + "#eligible-patients-section")

@slots_bp.route("/propose_slot/<slot_id>/<patient_id>", methods=["POST"])
@login_required
def propose_slot(slot_id, patient_id):
    """Marks a slot and patient as pending confirmation."""
    try:
        patient = patient_repo.get_by_id(patient_id, current_user.id)
        patient_name = patient.get("name", "Unknown") if patient else "Unknown"

        # Update slot status
        slot_success = slot_repo.update_status(
            slot_id, current_user.id, "pending", patient_id, patient_name
        )

        # Update patient status
        patient_success = patient_repo.update_status(
            patient_id, current_user.id, "pending", slot_id
        )

        if slot_success and patient_success:
            flash("Slot proposed and marked as pending confirmation.", "info")
            session.pop("current_appointment_id", None)
        else:
            raise Exception("Failed to update slot or patient status.")

    except Exception as e:
        logger.error(f"Error proposing slot: {e}", exc_info=True)
        flash("Error proposing slot. The slot may have been taken or the patient is no longer available.", "danger")
        # Attempt to roll back state if something went wrong
        slot_repo.update_status(slot_id, current_user.id, "available")
        patient_repo.update_status(patient_id, current_user.id, "waiting")

    return redirect(request.referrer or url_for('main.index'))

@slots_bp.route("/confirm_booking/<slot_id>/<patient_id>", methods=["POST"])
@login_required
def confirm_booking(slot_id, patient_id):
    """Confirms the booking, removing the patient and the slot."""
    try:
        # For safety, ensure the slot and patient are in the correct pending state before deleting.
        slot = slot_repo.get_by_id(slot_id)
        patient = patient_repo.get_by_id(patient_id, current_user.id)

        if not slot or not patient:
            raise Exception("Slot or patient not found.")

        if slot.get("proposed_patient_id") != patient_id or patient.get("proposed_slot_id") != slot_id:
            raise Exception("Mismatch in pending slot/patient data.")

        # If checks pass, delete both records.
        patient_repo.delete(patient_id, current_user.id)
        slot_repo.delete(slot_id, current_user.id)
        
        flash("Booking confirmed. Patient removed from patients list and slot closed.", "success")
    except Exception as e:
        logger.error(f"Error confirming booking: {e}", exc_info=True)
        flash("Error confirming booking. The slot or patient may have been modified.", "danger")

    return redirect(url_for("main.index"))

@slots_bp.route("/cancel_proposal/<slot_id>/<patient_id>", methods=["POST"])
@login_required
def cancel_proposal(slot_id, patient_id):
    """Cancels a pending proposal, making the slot and patient available again."""
    try:
        slot_success = slot_repo.update_status(slot_id, current_user.id, "available")
        patient_success = patient_repo.update_status(patient_id, current_user.id, "waiting")

        if slot_success and patient_success:
            flash("Proposal cancelled. Slot and patient are available again.", "info")
        else:
            raise Exception("Failed to reset slot or patient.")
            
    except Exception as e:
        logger.error(f"Error cancelling proposal: {e}", exc_info=True)
        flash("Error cancelling proposal. Please check the data and try again.", "danger")

    return redirect(request.referrer or url_for('main.index')) 