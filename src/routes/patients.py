from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from src.repositories.patient_repository import PatientRepository
from src.repositories.provider_repository import ProviderRepository
from src.services.matching_service import MatchingService
import csv
from io import StringIO
import logging

logger = logging.getLogger(__name__)

patients_bp = Blueprint('patients', __name__)
patient_repo = PatientRepository()
provider_repo = ProviderRepository()
matching_service = MatchingService()

@patients_bp.route("/add_patient", methods=["POST"])
@login_required
def add_patient():
    # --- Get Basic Info ---
    name = request.form.get("name")
    phone = request.form.get("phone")
    email = request.form.get("email")
    reason = request.form.get("reason")
    urgency = request.form.get("urgency")
    appointment_type = request.form.get("appointment_type")
    duration = request.form.get("duration")
    provider = request.form.get("provider")
    availability_mode = request.form.get("availability_mode", "available")

    # --- Process Availability ---
    availability_prefs = {}
    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    for day in days:
        day_lower = day.lower()
        am_checked = request.form.get(f"avail_{day_lower}_am")
        pm_checked = request.form.get(f"avail_{day_lower}_pm")
        periods = []
        if am_checked:
            periods.append("AM")
        if pm_checked:
            periods.append("PM")
        if periods:  # Only add day if AM or PM was selected
            availability_prefs[day] = periods

    logging.debug(f"Received availability days/times: {availability_prefs}")
    logging.debug(f"Received availability mode: {availability_mode}")

    # --- Basic Validation ---
    if not name or not phone:
        flash("Name and Phone are required.", "warning")
        return redirect(url_for("index") + "#add-patient-form")

    # --- Add Patient ---
    patient_data = {
        "name": name,
        "phone": phone,
        "email": email,
        "reason": reason,
        "urgency": urgency,
        "appointment_type": appointment_type,
        "duration": duration,
        "provider": provider,
        "availability": availability_prefs,
        "availability_mode": availability_mode,
        "user_id": current_user.id
    }
    
    result = patient_repo.create(patient_data)
    if result:
        flash("Patient added successfully.", "success")
    else:
        flash("Error adding patient.", "danger")

    return redirect(url_for("index") + "#add-patient-form")

@patients_bp.route("/remove_patient/<patient_id>", methods=["POST"])
@login_required
def remove_patient(patient_id):
    """Remove a patient from the patients list"""
    success = patient_repo.delete(patient_id, current_user.id)
    if success:
        flash("Patient removed successfully", "success")
    else:
        flash("Error removing patient", "danger")
    return redirect(url_for("index") + "#waitlist-table")

@patients_bp.route("/update_patient/<patient_id>", methods=["POST"])
@login_required
def update_patient(patient_id):
    """Update a patient's information"""
    patient = patient_repo.get_by_id(patient_id, current_user.id)
    if not patient:
        flash("Patient not found", "danger")
        return redirect(url_for("index"))
    
    name = request.form.get("name")
    phone = request.form.get("phone")
    email = request.form.get("email", "")
    provider = request.form.get("provider")
    appointment_type = request.form.get("appointment_type")
    duration = request.form.get("duration")
    urgency = request.form.get("urgency")
    reason = request.form.get("reason", "")
    availability_mode = request.form.get("availability_mode", "available")
    availability = {}
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for day in days:
        am_key = f"avail_{day}_am"
        pm_key = f"avail_{day}_pm"
        periods = []
        if am_key in request.form: periods.append("AM")
        if pm_key in request.form: periods.append("PM")
        if periods: availability[day.capitalize()] = periods
    
    update_data = {
        "name": name,
        "phone": phone,
        "email": email,
        "reason": reason,
        "urgency": urgency,
        "appointment_type": appointment_type,
        "duration": duration,
        "provider": provider,
        "availability": availability,
        "availability_mode": availability_mode
    }
    
    success = patient_repo.update(patient_id, current_user.id, update_data)
    if success:
        flash("Patient updated successfully", "success")
    else:
        flash("Error updating patient", "danger")
    return redirect(url_for("index"))

@patients_bp.route("/edit_patient/<patient_id>", methods=["GET"])
@login_required
def edit_patient(patient_id):
    """Show edit patient form"""
    patient = patient_repo.get_by_id(patient_id, current_user.id)
    if not patient:
        flash("Patient not found", "danger")
        return redirect(url_for("index"))
    
    providers = provider_repo.get_providers(current_user.id)
    return render_template("edit_patient.html", patient=patient, providers=providers)

@patients_bp.route("/upload_csv", methods=["GET", "POST"])
@login_required
def upload_csv():
    if request.method == "POST":
        if "patient_csv" not in request.files:
            flash("No file part", "warning")
            return redirect(request.url)
        file = request.files["patient_csv"]
        if file.filename == "":
            flash("No selected file", "warning")
            return redirect(request.url)

        if file and file.filename.endswith(".csv"):
            try:
                stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_input = csv.DictReader(stream)
                
                required_fields = ["name", "phone"]
                header = [h.lower().strip().replace(" ", "_") for h in (csv_input.fieldnames or [])]
                if not all(rf in header for rf in required_fields):
                    missing = ", ".join([rf for rf in required_fields if rf not in header])
                    flash(f"CSV missing required columns: {missing}.", "danger")
                    return redirect(url_for("index") + "#waitlist-table")

                patients_to_add = []
                
                # Fetch existing data for validation and duplicate checks
                existing_patients = patient_repo.get_waitlist(current_user.id)
                existing_patients_set = set((p['name'].lower(), p['phone']) for p in existing_patients)
                
                providers = provider_repo.get_providers(current_user.id)
                valid_providers = {f"{p['first_name']} {p['last_initial'] or ''}".strip().lower() for p in providers}
                valid_providers.add("no preference")

                valid_appointment_types = {apt['appointment_type'].lower().replace(' ', '_') for apt in (current_user.appointment_types_data or [])}

                # Validation helpers
                def validate_provider(val):
                    return val if (val or "no preference").lower() in valid_providers else "no preference"

                for row in csv_input:
                    norm_row = {k.lower().strip().replace(" ", "_"): v for k, v in row.items()}
                    name, phone = norm_row.get("name", "").strip(), norm_row.get("phone", "").strip()

                    if not name or not phone or (name.lower(), phone) in existing_patients_set:
                        continue
                
                    # Add user_id to each record for insertion
                    patient_data = {
                        "user_id": current_user.id,
                        "name": name,
                        "phone": phone,
                        "email": norm_row.get("email", ""),
                        "reason": norm_row.get("reason", ""),
                        "urgency": norm_row.get("urgency", "medium").lower(),
                        "appointment_type": norm_row.get("appointment_type", "custom"),
                        "duration": norm_row.get("duration", "30"),
                        "provider": validate_provider(norm_row.get("provider")),
                    }
                    patients_to_add.append(patient_data)
                    existing_patients_set.add((name.lower(), phone))

                if patients_to_add:
                    added_patients = patient_repo.bulk_create(patients_to_add)
                    added_count = len(added_patients)
                    skipped_count = csv_input.line_num - 1 - added_count
                    flash(f"Successfully added {added_count} new patients. Skipped {skipped_count} rows.", "success")
                else:
                    flash("No new patients to add from the CSV file.", "info")

            except Exception as e:
                flash(f"An error occurred during CSV processing: {e}", "danger")
        else:
            flash("Invalid file format. Please upload a .csv file.", "danger")
        
        return redirect(url_for("index") + "#waitlist-table")
    
    return redirect(url_for("index") + "#csv-upload-section")

@patients_bp.route("/api/find_matches_for_patient/<patient_id>")
@login_required
def api_find_matches_for_patient(patient_id):
    try:
        # Get matching slots for the patient
        matching_slots = matching_service.find_matches_for_patient(patient_id, current_user.id)
        
        # Get provider names for display
        provider_map = provider_repo.get_provider_map(current_user.id)
        
        # Format slots for JSON response
        formatted_slots = []
        for slot in matching_slots:
            formatted_slot = {
                'id': slot['id'],
                'date': slot['date'],
                'time': slot['time'],
                'duration': slot['duration'],
                'provider_name': provider_map.get(str(slot.get('provider')), 'Unknown'),
                'notes': slot.get('notes', '')
            }
            formatted_slots.append(formatted_slot)
        
        return jsonify({
            'slots': formatted_slots,
            'count': len(formatted_slots)
        })
        
    except Exception as e:
        logger.error(f"Error finding matches for patient {patient_id}: {e}")
        return jsonify({"error": "Failed to find matches"}), 500 