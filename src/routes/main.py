from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from src.decorators.trial_required import trial_required
from src.repositories.patient_repository import PatientRepository
from src.repositories.provider_repository import ProviderRepository
from src.repositories.slot_repository import SlotRepository
from src.utils.helpers import wait_time_to_days
from src.services.trial_service import trial_service
import logging
import json

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)
patient_repo = PatientRepository()
provider_repo = ProviderRepository()
slot_repo = SlotRepository()

@main_bp.route("/", methods=["GET"])
@trial_required
def index():
    """Main dashboard page."""
    try:
        # Get user-specific data
        waitlist = patient_repo.get_waitlist(current_user.id)
        providers = provider_repo.get_providers(current_user.id)
        
        # Enrich patient data with slot details for pending patients
        for patient in waitlist:
            if patient.get('status') == 'pending' and patient.get('proposed_slot_id'):
                slot_details = slot_repo.get_by_id(patient['proposed_slot_id'])
                if slot_details:
                    # Format slot details for display
                    date_str = slot_details.get('date', 'Unknown Date')
                    time_str = slot_details.get('start_time', '')
                    provider_name = slot_details.get('provider', 'Unknown Provider')
                    
                    # Add day of the week to the date
                    try:
                        from datetime import datetime
                        if date_str != 'Unknown Date':
                            date_obj = datetime.fromisoformat(date_str)
                            day_of_week = date_obj.strftime('%a')  # Short day name (Mon, Tue, etc.)
                            formatted_date = date_obj.strftime('%m/%d')  # MM/DD format
                            date_display = f"{day_of_week} {formatted_date}"
                        else:
                            date_display = date_str
                    except:
                        date_display = date_str
                    
                    if time_str:
                        patient['proposed_slot_details'] = f"{date_display} at {time_str} w/ {provider_name}"
                    else:
                        patient['proposed_slot_details'] = f"{date_display} w/ {provider_name}"
        
        # Parse appointment types data from user
        appointment_types_data = []
        if current_user.appointment_types_data:
            try:
                appointment_types_data = json.loads(current_user.appointment_types_data)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing appointment_types_data for user {current_user.id}: {e}")
                appointment_types_data = []
        
        # Sort waitlist by wait time and urgency
        def sort_key_waitlist(p):
            urgency_order = {'high': 0, 'medium': 1, 'low': 2}
            urgency = urgency_order.get(p.get('urgency', 'medium'), 1)
            wait_days = wait_time_to_days(p.get('wait_time', '0 days'))
            name = p.get('name', '').lower()
            return (urgency, -wait_days, name)
        
        waitlist.sort(key=sort_key_waitlist)
        
        # Get trial status for warnings
        trial_status = trial_service.get_trial_status(current_user)
        
        return render_template(
            "index.html",
            waitlist=waitlist,
            providers=providers,
            has_providers=len(providers) > 0,
            appointment_types_data=appointment_types_data,
            current_user_name=current_user.user_name_for_message or "the scheduling team",
            current_clinic_name=current_user.clinic_name or "our clinic",
            trial_status=trial_status
        )
    except Exception as e:
        # This is a fallback for unexpected errors.
        logging.error(f"A critical error occurred in the index route: {e}", exc_info=True)
        flash("A critical error occurred. Please try logging in again.", "danger")
        return redirect(url_for('auth.login')) 