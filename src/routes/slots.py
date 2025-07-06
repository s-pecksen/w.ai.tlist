from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from src.repositories.slot_repository import SlotRepository
from src.repositories.patient_repository import PatientRepository
from src.repositories.provider_repository import ProviderRepository
from src.services.matching_service import MatchingService
from datetime import datetime, timedelta
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
    logger.info(f"\n\n\n\n\nSLOTS REQUEST SENT!\n\n\n\n\n")
    """Display slots page with available slots and matching functionality."""
    try:
        logger.info("1")
        # Get all slots for the user
        all_slots = slot_repo.get_all_slots(current_user.id)
        logger.info("2")
        # Get providers for display
        providers = provider_repo.get_providers(current_user.id)
        logger.info("3")
        
        # Get current appointment ID from session for matching
        current_appointment_id = session.get("current_appointment_id")
        logger.info("5")
        # If we have a current appointment, find matches
        eligible_patients = []
        ineligible_patients = []
        current_slot = None
        logger.info("6")
        if current_appointment_id:
            current_slot = slot_repo.get_by_id(current_appointment_id)
            if current_slot:
                # Add time field for template compatibility
                current_slot['time'] = current_slot.get('start_time', '')
                eligible_patients, ineligible_patients = matching_service.find_matches_for_slot(
                    current_appointment_id, current_user.id
                )
        logger.info("7")
        # Get all waiting patients for the general list
        waiting_patients = patient_repo.get_by_status(current_user.id, "waiting")
        logger.info("8")
        logger.info(f"SLOTS TO DISPLAY: {all_slots}")

        # Enrich slots with provider_name for display and add time field for template compatibility
        for slot in all_slots:
            # Since we now store provider names directly, just use the stored name
            slot['provider_name'] = slot.get('provider', 'Unknown Provider')
            # Add time field for template compatibility (using start_time in 24-hour format)
            slot['time'] = slot.get('start_time', '')
            # Ensure start_time is also available for consistency
            if 'start_time' not in slot:
                slot['start_time'] = slot.get('time', '')
        
        return render_template(
            "slots.html",
            slots=all_slots,
            providers=providers,
            has_providers=len(providers) > 0,
            eligible_patients=eligible_patients,
            ineligible_patients=ineligible_patients,
            waiting_patients=waiting_patients,
            current_appointment=current_slot,  # Template expects current_appointment
            current_user_name=current_user.user_name_for_message or "the scheduling team"
        )
    except Exception as e:
        logger.error(f"\n\n\n\n\nA critical error occurred in the slots route: {e}", exc_info=True)
        flash("A critical error occurred. Please try again.", "danger")
        return redirect(url_for('main.index'))

@slots_bp.route("/add_cancelled_appointment", methods=["POST"])
@login_required
def add_cancelled_appointment():
    """Add a new cancelled appointment (open slot)"""
    provider_id = request.form.get("provider")
    slot_date = request.form.get("date")
    slot_time_str = request.form.get("time")
    duration = request.form.get("duration")
    notes = request.form.get("notes", "")

    if not all([provider_id, slot_date, slot_time_str, duration]):
        flash("All required fields must be filled", "danger")
        return redirect(url_for("slots.slots"))

    # Convert provider ID to provider name
    provider = provider_repo.get_by_id(provider_id)
    if not provider:
        flash("Invalid provider selected", "danger")
        return redirect(url_for("slots.slots"))
    
    provider_name = f"{provider['first_name']} {provider['last_initial'] or ''}".strip()

    # Validate time format (24-hour)
    try:
        time_obj = datetime.strptime(slot_time_str, "%H:%M").time()
        start_time = time_obj.strftime("%H:%M")
    except ValueError:
        flash("Invalid time format. Please use HH:MM (24-hour format).", "danger")
        return redirect(url_for("slots.slots"))
    
    try:
        slot_data = {
            "provider": provider_name,
            "start_time": start_time,
            "date": slot_date,
            "duration": duration,
            "notes": notes,
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
    provider_id = request.form.get("provider")
    slot_date = request.form.get("date")
    slot_time_str = request.form.get("time")
    duration = request.form.get("duration")
    notes = request.form.get("notes", "")

    if not all([provider_id, slot_date, slot_time_str, duration]):
        flash("All required fields must be filled", "danger")
        return redirect(url_for("slots.slots"))

    # Convert provider ID to provider name
    provider = provider_repo.get_by_id(provider_id)
    if not provider:
        flash("Invalid provider selected", "danger")
        return redirect(url_for("slots.slots"))
    
    provider_name = f"{provider['first_name']} {provider['last_initial'] or ''}".strip()

    # Validate time format (24-hour)
    try:
        time_obj = datetime.strptime(slot_time_str, "%H:%M").time()
        start_time = time_obj.strftime("%H:%M")
    except ValueError:
        flash("Invalid time format. Please use HH:MM (24-hour format).", "danger")
        return redirect(url_for("slots.slots"))
    
    # Calculate start_time and end_time
    try:
        start_dt = datetime.strptime(slot_time_str, "%H:%M")
        end_dt = start_dt + timedelta(minutes=int(duration))
        start_time = start_dt.strftime("%H:%M")
        end_time = end_dt.strftime("%H:%M")
    except Exception as e:
        flash(f"Error calculating end time: {e}", "danger")
        return redirect(url_for("slots.slots"))

    try:
        update_data = {
            "provider": provider_name,
            "date": slot_date,
            "start_time": start_time,
            "duration": duration,
            "notes": notes
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