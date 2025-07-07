from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from src.repositories.patient_repository import PatientRepository
from src.repositories.provider_repository import ProviderRepository
from src.utils.helpers import wait_time_to_days
import logging
import json

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)
patient_repo = PatientRepository()
provider_repo = ProviderRepository()

@main_bp.route("/", methods=["GET"])
@login_required
def index():
    """Main dashboard page."""
    try:
        # Debug current_user attributes
        logger.debug(f"Current user ID: {current_user.id}")
        logger.debug(f"Current user clinic_name: '{current_user.clinic_name}'")
        logger.debug(f"Current user user_name_for_message: '{current_user.user_name_for_message}'")
        
        # Get user-specific data
        waitlist = patient_repo.get_waitlist(current_user.id)
        providers = provider_repo.get_providers(current_user.id)
        
        # Parse appointment types data from user
        appointment_types_data = []
        if current_user.appointment_types_data:
            try:
                appointment_types_data = json.loads(current_user.appointment_types_data)
                logger.debug(f"Successfully parsed appointment_types_data for user {current_user.id}: {appointment_types_data}")
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing appointment_types_data for user {current_user.id}: {e}")
                appointment_types_data = []
        else:
            logger.debug(f"No appointment_types_data found for user {current_user.id}")
        
        # Sort waitlist by wait time and urgency
        def sort_key_waitlist(p):
            urgency_order = {'high': 0, 'medium': 1, 'low': 2}
            urgency = urgency_order.get(p.get('urgency', 'medium'), 1)
            wait_days = wait_time_to_days(p.get('wait_time', '0 days'))
            name = p.get('name', '').lower()
            return (urgency, -wait_days, name)
        
        waitlist.sort(key=sort_key_waitlist)
        
        return render_template(
            "index.html",
            waitlist=waitlist,
            providers=providers,
            has_providers=len(providers) > 0,
            appointment_types_data=appointment_types_data,
            current_user_name=current_user.user_name_for_message or "the scheduling team",
            current_clinic_name=current_user.clinic_name or "our clinic"
        )
    except Exception as e:
        # This is a fallback for unexpected errors.
        logging.error(f"A critical error occurred in the index route: {e}", exc_info=True)
        flash("A critical error occurred. Please try logging in again.", "danger")
        return redirect(url_for('auth.login')) 