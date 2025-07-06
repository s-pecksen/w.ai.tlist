from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from src.repositories.user_repository import UserRepository
import json
import logging

logger = logging.getLogger(__name__)

appointment_types_bp = Blueprint('appointment_types', __name__)
user_repo = UserRepository()

@appointment_types_bp.route("/appointment_types", methods=["GET"])
@login_required
def list_appointment_types():
    """Display appointment types management page."""
    # Get current appointment types from user
    appointment_types_data = []
    if current_user.appointment_types_data:
        try:
            appointment_types_data = json.loads(current_user.appointment_types_data)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing appointment_types_data for user {current_user.id}: {e}")
            appointment_types_data = []
    
    return render_template("appointment_types.html", appointment_types=appointment_types_data)

@appointment_types_bp.route("/add_appointment_type", methods=["POST"])
@login_required
def add_appointment_type():
    """Add a new appointment type."""
    appointment_type = request.form.get("appointment_type", "").strip()
    durations_str = request.form.get("durations", "").strip()

    if not appointment_type:
        flash("Appointment type name is required", "warning")
        return redirect(url_for("appointment_types.list_appointment_types"))

    # Parse durations
    durations = []
    if durations_str:
        try:
            durations = [int(d.strip()) for d in durations_str.split(',') if d.strip() and d.strip().isdigit()]
        except ValueError:
            flash("Invalid duration format. Use numbers separated by commas (e.g., 30,60,90)", "warning")
            return redirect(url_for("appointment_types.list_appointment_types"))

    # Default to 30 minutes if no durations specified
    if not durations:
        durations = [30]

    try:
        # Get current appointment types
        current_types = []
        if current_user.appointment_types_data:
            try:
                current_types = json.loads(current_user.appointment_types_data)
            except json.JSONDecodeError:
                current_types = []

        # Check if appointment type already exists
        existing_type = next((t for t in current_types if t.get('appointment_type', '').lower() == appointment_type.lower()), None)
        if existing_type:
            flash(f"Appointment type '{appointment_type}' already exists", "warning")
            return redirect(url_for("appointment_types.list_appointment_types"))

        # Add new appointment type
        new_type = {
            'appointment_type': appointment_type,
            'durations': durations
        }
        current_types.append(new_type)

        # Update user's appointment types
        appointment_types_list = [t.get('appointment_type', '') for t in current_types]
        
        update_data = {
            'appointment_types': json.dumps(appointment_types_list),
            'appointment_types_data': json.dumps(current_types)
        }
        
        success = user_repo.update(current_user.id, update_data)
        if success:
            flash("Appointment type added successfully", "success")
        else:
            flash("Error adding appointment type", "danger")
            
    except Exception as e:
        logger.error(f"Error adding appointment type: {e}")
        flash("An error occurred while adding the appointment type", "danger")

    return redirect(url_for("appointment_types.list_appointment_types"))

@appointment_types_bp.route("/remove_appointment_type", methods=["POST"])
@login_required
def remove_appointment_type():
    """Remove an appointment type."""
    appointment_type = request.form.get("appointment_type", "").strip()
    
    if not appointment_type:
        flash("Appointment type is required", "warning")
        return redirect(url_for("appointment_types.list_appointment_types"))

    try:
        # Get current appointment types
        current_types = []
        if current_user.appointment_types_data:
            try:
                current_types = json.loads(current_user.appointment_types_data)
            except json.JSONDecodeError:
                current_types = []

        # Remove the appointment type
        updated_types = [t for t in current_types if t.get('appointment_type', '').lower() != appointment_type.lower()]
        
        if len(updated_types) == len(current_types):
            flash("Appointment type not found", "warning")
            return redirect(url_for("appointment_types.list_appointment_types"))

        # Update user's appointment types
        appointment_types_list = [t.get('appointment_type', '') for t in updated_types]
        
        update_data = {
            'appointment_types': json.dumps(appointment_types_list),
            'appointment_types_data': json.dumps(updated_types)
        }
        
        success = user_repo.update(current_user.id, update_data)
        if success:
            flash("Appointment type removed successfully", "success")
        else:
            flash("Error removing appointment type", "danger")
            
    except Exception as e:
        logger.error(f"Error removing appointment type: {e}")
        flash("An error occurred while removing the appointment type", "danger")

    return redirect(url_for("appointment_types.list_appointment_types"))

@appointment_types_bp.route("/edit_appointment_type", methods=["POST"])
@login_required
def edit_appointment_type():
    """Edit an existing appointment type."""
    old_appointment_type = request.form.get("old_appointment_type", "").strip()
    new_appointment_type = request.form.get("new_appointment_type", "").strip()
    durations_str = request.form.get("durations", "").strip()

    if not old_appointment_type or not new_appointment_type:
        flash("Appointment type name is required", "warning")
        return redirect(url_for("appointment_types.list_appointment_types"))

    # Parse durations
    durations = []
    if durations_str:
        try:
            durations = [int(d.strip()) for d in durations_str.split(',') if d.strip() and d.strip().isdigit()]
        except ValueError:
            flash("Invalid duration format. Use numbers separated by commas (e.g., 30,60,90)", "warning")
            return redirect(url_for("appointment_types.list_appointment_types"))

    # Default to 30 minutes if no durations specified
    if not durations:
        durations = [30]

    try:
        # Get current appointment types
        current_types = []
        if current_user.appointment_types_data:
            try:
                current_types = json.loads(current_user.appointment_types_data)
            except json.JSONDecodeError:
                current_types = []

        # Find and update the appointment type
        type_found = False
        for t in current_types:
            if t.get('appointment_type', '').lower() == old_appointment_type.lower():
                t['appointment_type'] = new_appointment_type
                t['durations'] = durations
                type_found = True
                break

        if not type_found:
            flash("Appointment type not found", "warning")
            return redirect(url_for("appointment_types.list_appointment_types"))

        # Check if new name conflicts with existing types (excluding the one being edited)
        existing_names = [t.get('appointment_type', '').lower() for t in current_types]
        if existing_names.count(new_appointment_type.lower()) > 1:
            flash(f"Appointment type '{new_appointment_type}' already exists", "warning")
            return redirect(url_for("appointment_types.list_appointment_types"))

        # Update user's appointment types
        appointment_types_list = [t.get('appointment_type', '') for t in current_types]
        
        update_data = {
            'appointment_types': json.dumps(appointment_types_list),
            'appointment_types_data': json.dumps(current_types)
        }
        
        success = user_repo.update(current_user.id, update_data)
        if success:
            flash("Appointment type updated successfully", "success")
        else:
            flash("Error updating appointment type", "danger")
            
    except Exception as e:
        logger.error(f"Error updating appointment type: {e}")
        flash("An error occurred while updating the appointment type", "danger")

    return redirect(url_for("appointment_types.list_appointment_types")) 