from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime, timedelta, date
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import keyring
import os
import pandas as pd
import csv
from io import StringIO
from provider_manager import ProviderManager
import uuid
from patient_waitlist_manager import PatientWaitlistManager
import shutil
import glob
import logging
from cancelled_slot_manager import CancelledSlotManager
import json # Needed for handling availability JSON in CSV upload

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Make sure to add this for flash messages to work
app.config['SESSION_TYPE'] = 'filesystem'

# Initialize the ProviderManager
provider_manager = ProviderManager()

# Define paths
# test_csv_path = 'Tests/patient_waitlist.csv' # Removed test path
backup_dir = 'waitlist_backups'
cancelled_slots_backup_dir = 'cancelled_slots_backups'

# Initialize PatientWaitlistManager
waitlist_manager = PatientWaitlistManager("ClinicWaitlistApp", backup_dir=backup_dir)

# Initialize CancelledSlotManager
slot_manager = CancelledSlotManager(backup_dir=cancelled_slots_backup_dir)

# Create Base before any classes that need to inherit from it
Base = declarative_base()

# Database setup with encryption
class SecureDatabase:
    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher_suite = Fernet(self.key)
        self.engine = create_engine('sqlite:///clinic_data.db')
        
    def _get_or_create_key(self):
        key = keyring.get_password("clinic_scheduler", "db_key")
        if not key:
            key = Fernet.generate_key()
            keyring.set_password("clinic_scheduler", "db_key", key)
        return key
    
    def encrypt_data(self, data):
        return self.cipher_suite.encrypt(data.encode())
    
    def decrypt_data(self, encrypted_data):
        return self.cipher_suite.decrypt(encrypted_data).decode()

# Patient data model
class Patient(Base):
    __tablename__ = 'patients'
    
    id = Column(String, primary_key=True)
    encrypted_data = Column(String)
    created_at = Column(DateTime)

# Add this helper function to convert wait time to minutes
def wait_time_to_minutes(wait_time_str):
    total_minutes = 0
    if not isinstance(wait_time_str, str): # Check for non-string input
        return 0

    remaining = wait_time_str # Start with the full string

    if 'days' in remaining:
        try:
            parts = remaining.split('days')
            days = int(parts[0].strip())
            total_minutes += days * 24 * 60 # INSIDE try
            # Update remaining string ONLY if days parsing succeeds
            if len(parts) > 1 and ',' in parts[1]:
                remaining = parts[1].split(',')[1].strip()
        except (ValueError, IndexError):
            # Handle error: print a warning, keep original 'remaining' for next steps
            print(f"Warning: Could not parse days from '{wait_time_str}'.")
            remaining = wait_time_str # Fallback to original if days parsing failed

    # Process hours from the potentially updated 'remaining' string
    if 'hours' in remaining:
        try:
            parts = remaining.split('hours')
            hours = int(parts[0].strip())
            total_minutes += hours * 60 # INSIDE try
            # Update remaining string ONLY if hours parsing succeeds
            if len(parts) > 1 and ',' in parts[1]:
                remaining = parts[1].split(',')[1].strip()
            else:
                remaining = '' # Successfully parsed 'X hours', nothing left for mins
        except (ValueError, IndexError):
             # Handle error: print warning, proceed to minutes with current 'remaining'
             print(f"Warning: Could not parse hours from '{remaining}'.")
             # No need to reset 'remaining', just let minute parsing try

    # Process minutes from the potentially updated 'remaining' string
    if 'minutes' in remaining:
        try:
            minutes = int(remaining.split('minutes')[0].strip())
            total_minutes += minutes
        except (ValueError, IndexError):
             # Handle error: print warning
             print(f"Warning: Could not parse minutes from '{remaining}'.")
        
    return total_minutes

@app.route('/', methods=['GET'])
def index():
    logging.debug("Entering index route")
    try:
        # Update wait times first
        waitlist_manager.update_wait_times()
        
        # Get all providers (list of dictionaries {'name': 'Provider Name'})
        all_providers = provider_manager.get_provider_list()
        
        # Check if we have any providers at all
        has_providers = len(all_providers) > 0
        
        # Get the waitlist from manager
        waitlist = waitlist_manager.get_all_patients()
        logging.debug(f"Index route: Fetched {len(waitlist)} patients")
        
        # Sort waitlist: emergencies first, then by wait time (longest first), then scheduled last
        def sort_key_safe(x):
            try:
                wait_minutes = -wait_time_to_minutes(x.get('wait_time', '0 minutes'))
                is_scheduled = x.get('status') == 'scheduled'
                # Correctly check for emergency type using .get()
                is_emergency = x.get('appointment_type', '').lower() == 'emergency_exam' # Match exact type
                # Sort order: Scheduled (True) last, Emergency (False means emergency comes first) first, then by wait time
                return (is_scheduled, not is_emergency, wait_minutes)
            except Exception as e:
                logging.error(f"Error calculating sort key for patient {x.get('id')}: {e}", exc_info=True)
                return (True, True, 0) # Default sort value on error

        sorted_waitlist = sorted(waitlist, key=sort_key_safe)
        
        # Show a different message if there are providers but they're all inactive
        if not has_providers:
            flash('Please upload a list of Provider names to proceed', 'warning')
        
        logging.debug("Index route: Rendering index.html")
        return render_template('index.html', 
                              waitlist=sorted_waitlist, 
                              providers=all_providers,
                              has_providers=has_providers)
    except Exception as e:
        logging.error(f"Exception in index route: {e}", exc_info=True)
        flash('An error occurred while loading the main page.', 'danger')
        # Render a simpler template or redirect to an error page if possible
        # For now, just return a simple error message
        return "<h1>An error occurred</h1><p>Please check the server logs.</p>", 500

@app.route('/add_patient', methods=['POST'])
def add_patient():
    try:
        # --- Get Basic Info ---
        name = request.form.get('name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        reason = request.form.get('reason')
        urgency = request.form.get('urgency')
        appointment_type = request.form.get('appointment_type')
        duration = request.form.get('duration')
        provider = request.form.get('provider')
        availability_mode = request.form.get('availability_mode', 'available') # Get the mode ('available' or 'unavailable')

        # --- Process Availability ---
        # Structure: {'Monday': ['AM', 'PM'], 'Tuesday': ['AM'], ...}
        availability_prefs = {}
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in days:
            day_lower = day.lower()
            am_checked = request.form.get(f'avail_{day_lower}_am')
            pm_checked = request.form.get(f'avail_{day_lower}_pm')
            periods = []
            if am_checked:
                periods.append('AM')
            if pm_checked:
                periods.append('PM')
            if periods: # Only add day if AM or PM was selected
                availability_prefs[day] = periods

        logging.debug(f"Received availability days/times: {availability_prefs}")
        logging.debug(f"Received availability mode: {availability_mode}")

        # --- Basic Validation ---
        if not name or not phone:
            flash('Name and Phone are required to add a patient.', 'warning')
            return redirect(url_for('index') + '#add-patient-form')

        # --- Add Patient via Manager ---
        # Use the waitlist manager to add the patient, including structured availability and mode
        new_patient = waitlist_manager.add_patient(
            name=name,
            phone=phone,
            email=email,
            reason=reason,
            urgency=urgency,
            appointment_type=appointment_type,
            duration=duration,
            provider=provider,
            availability=availability_prefs, # Pass the dictionary
            availability_mode=availability_mode # Pass the mode
        )

        if new_patient:
            flash('Patient added successfully.', 'success')
        else:
            # Manager logs the specific error
            flash('Failed to add patient. Please check logs.', 'danger')

    except Exception as e:
        logging.error(f"Error in add_patient route: {e}", exc_info=True)
        flash('An unexpected error occurred while adding the patient.', 'danger')

    return redirect(url_for('index') + '#add-patient-form')

# Update the schedule_patient route
@app.route('/schedule_patient/<patient_id>', methods=['POST'])
def schedule_patient(patient_id):
    # Update wait times first
    waitlist_manager.update_wait_times()
    
    # Schedule the patient using manager
    if waitlist_manager.schedule_patient(patient_id):
        flash('Patient scheduled successfully.', 'success')
    else:
        flash('Failed to schedule patient.', 'danger')
    # Redirect back to the index page, focusing on the waitlist table
    return redirect(url_for('index') + '#waitlist-table') # Added fragment

# Update the remove_patient route
@app.route('/remove_patient/<patient_id>', methods=['POST'])
def remove_patient(patient_id):
    if waitlist_manager.remove_patient(patient_id):
        flash('Patient removed successfully.', 'success')
    else:
        flash('Failed to remove patient.', 'danger')
    # Redirect back to the index page, focusing on the waitlist table
    return redirect(url_for('index') + '#waitlist-table') # Added fragment

# --- Add New Route for Manual Backup ---
@app.route('/save_backup', methods=['POST'])
def save_backup():
    """Manually saves a timestamped backup of the waitlist."""
    try:
        waitlist_manager.save_backup()
        flash('Waitlist backup saved successfully.', 'success')
    except Exception as e:
        print(f"Error during manual backup: {str(e)}")
        flash(f'Error saving backup: {str(e)}', 'danger')
    # Redirect back to index, maybe near the top or an actions area
    return redirect(url_for('index') + '#page-top') # Added fragment (use a relevant ID)
# --- End New Route ---

# Add these helper functions
def validate_appointment_type(value):
    # Updated valid types based on user request
    valid_types = ['hygiene', 'recall', 'resto', 'x-ray', 'np_spec', 'spec_exam', 'emergency_exam', 'rct', 'custom'] 
    value_str = str(value).lower().strip()
    # Defaulting to 'hygiene' as a common type if the provided one isn't valid
    return value_str if value_str in valid_types else 'hygiene' 

def validate_duration(value):
    # Use the updated list of durations from the HTML forms
    valid_durations = ['30', '60', '70', '90', '120'] 
    return str(value) if str(value) in valid_durations else '30'

def validate_provider(value):
    # Get the list of valid providers from the provider manager
    # Now retrieves dictionaries [{'name': 'Provider Name'}]
    valid_providers_list = provider_manager.get_provider_list()
    valid_provider_names = ['no preference'] + [p.get('name', '').lower() for p in valid_providers_list]

    # Convert empty string or None to 'no preference'
    provider_value_lower = (value or '').strip().lower()
    if not provider_value_lower or provider_value_lower == 'no preference':
        return 'no preference'

    # Check if the provided value is in our list (case-insensitive)
    if provider_value_lower in valid_provider_names:
         # Find the original casing from the manager's list
        for p_dict in valid_providers_list:
            if p_dict.get('name', '').lower() == provider_value_lower:
                return p_dict['name'] # Return correctly cased name
        # Fallback if somehow not found after check (shouldn't happen)
        return value.strip()

    # Default to 'no preference' if not found
    return 'no preference'

def validate_urgency(value):
    valid_urgency = ['low', 'medium', 'high']
    return value.lower() if value.lower() in valid_urgency else 'medium'

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    print("--- DEBUG: /upload_csv route hit ---")
    if not provider_manager.get_provider_list():
        flash('Please add providers before uploading patient data', 'warning')
        return redirect(url_for('index'))
    
    if 'csv_file' not in request.files:
        flash('No file selected for upload.', 'warning')
        return redirect(url_for('index'))
    
    file = request.files['csv_file']
    if file.filename == '':
        flash('No file selected for upload.', 'warning')
        return redirect(url_for('index'))

    if file and file.filename.endswith('.csv'):
        try:
            stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
            reader = csv.DictReader(stream)
            added_count = 0
            skipped_count = 0
            required_columns = ['name', 'phone'] # Minimum required

            existing_patients_list = waitlist_manager.get_all_patients()
            existing_patients_set = {(p.get('name', '').strip(), p.get('phone', '').strip())
                                     for p in existing_patients_list if p.get('name') and p.get('phone')}
            print(f"--- DEBUG: Found {len(existing_patients_set)} existing patients for duplicate check ---")

            patients_to_add = []
            headers = reader.fieldnames or []
            print(f"--- DEBUG: CSV Headers: {headers} ---")
            if not all(col in headers for col in required_columns):
                 flash(f'CSV must contain at least {", ".join(required_columns)} columns', 'danger')
                 return redirect(url_for('index'))

            print("--- DEBUG: Required columns check passed ---")
            has_availability_col = 'availability' in headers
            has_mode_col = 'availability_mode' in headers

            for row in reader:
                 csv_name = row.get('name', '').strip()
                 csv_phone = row.get('phone', '').strip()
                 if not csv_name or not csv_phone:
                     print(f"--- DEBUG: Skipping row due to missing name/phone: {row} ---")
                     skipped_count += 1
                     continue
                 if (csv_name, csv_phone) in existing_patients_set:
                     print(f"--- DEBUG: Skipping duplicate patient: {csv_name}, {csv_phone} ---")
                     skipped_count += 1
                     continue

                 provider_value = row.get('provider', '')

                 # --- Try parsing timestamp ---
                 datetime_str = row.get('date_time_entered', '').strip()
                 parsed_timestamp = None
                 if datetime_str:
                    try:
                        # Combined parsing attempts
                        parsed_timestamp = datetime.fromisoformat(datetime_str)
                    except ValueError:
                        possible_formats = [
                            '%m/%d/%Y %H:%M:%S', '%#m/%#d/%Y %#H:%M:%S',
                            '%m/%d/%y %I:%M %p', '%m/%d/%Y %I:%M %p'
                        ]
                        for fmt in possible_formats:
                            try:
                                parsed_timestamp = datetime.strptime(datetime_str, fmt)
                                break
                            except ValueError:
                                continue
                        if not parsed_timestamp:
                            print(f"--- DEBUG: Could not parse timestamp '{datetime_str}' for patient {csv_name} ---")

                 # --- Parse availability from CSV ---
                 # Expects availability column to contain JSON string like '{"Monday": ["AM", "PM"]}'
                 # or potentially older format like comma-separated days ('Monday, Tuesday')
                 availability_data = {}
                 if has_availability_col:
                     availability_str = row.get('availability', '').strip()
                     if availability_str:
                         try:
                             # Try parsing as JSON first
                             loaded_avail = json.loads(availability_str)
                             if isinstance(loaded_avail, dict):
                                 # Validate structure (ensure values are lists)
                                 availability_data = {k: v for k, v in loaded_avail.items() if isinstance(v, list)}
                             else:
                                 print(f"--- DEBUG: Parsed availability JSON for {csv_name} is not a dict: '{availability_str}' ---")
                         except json.JSONDecodeError:
                             # Fallback: Try parsing as simple comma-separated days (implies full day availability)
                             # This is for backward compatibility; new uploads should use JSON.
                             print(f"--- DEBUG: Failed to parse availability as JSON for {csv_name}, trying comma-separated: '{availability_str}' ---")
                             days_list = [day.strip() for day in availability_str.split(',') if day.strip()]
                             if days_list:
                                # Assume AM and PM if parsed this old way
                                availability_data = {day: ['AM', 'PM'] for day in days_list}


                 # --- Parse availability_mode from CSV ---
                 # Defaults to 'available' if column missing or value invalid
                 availability_mode = 'available'
                 if has_mode_col:
                     mode_raw = row.get('availability_mode', '').strip().lower()
                     if mode_raw in ['available', 'unavailable']:
                         availability_mode = mode_raw

                 patients_to_add.append({
                    'name': csv_name,
                    'phone': csv_phone,
                    'email': row.get('email', ''),
                    'reason': row.get('reason', ''),
                    'urgency': validate_urgency(row.get('urgency', 'medium')),
                    'appointment_type': validate_appointment_type(row.get('appointment_type')),
                    'duration': validate_duration(row.get('duration', '30')),
                    'provider': validate_provider(provider_value),
                    'timestamp': parsed_timestamp,
                    'availability': availability_data, # Pass parsed dict
                    'availability_mode': availability_mode # Pass parsed mode
                 })
                 added_count += 1
                 existing_patients_set.add((csv_name, csv_phone))

            print(f"--- DEBUG: Finished reading rows. Added: {added_count}, Skipped: {skipped_count} ---")

            if patients_to_add:
                print(f"--- DEBUG: Adding {len(patients_to_add)} new patients to manager ---")
                for p_data in patients_to_add:
                    # Extract specific args for manager method
                    patient_timestamp = p_data.pop('timestamp', None)
                    patient_availability = p_data.pop('availability', {})
                    patient_mode = p_data.pop('availability_mode', 'available')
                    waitlist_manager.add_patient(
                        timestamp=patient_timestamp,
                        availability=patient_availability,
                        availability_mode=patient_mode,
                        **p_data
                    )

            print("--- DEBUG: Finished adding patients to manager ---")
            # Update Flash Message (logic unchanged)
            if added_count > 0 and skipped_count > 0:
                 flash(f'Successfully added {added_count} new patients. Skipped {skipped_count} duplicates or rows with missing info.', 'success')
            elif added_count > 0:
                 flash(f'Successfully added {added_count} new patients from CSV.', 'success')
            elif skipped_count > 0:
                 flash(f'No new patients added. Skipped {skipped_count} duplicates or rows with missing info.', 'info')
            else:
                 flash('No patients added from CSV.', 'info')

        except Exception as e:
            print(f"--- DEBUG: Exception caught in /upload_csv: {str(e)} ---") # Added print
            logging.error(f"Error processing patient CSV: {str(e)}", exc_info=True) # Use logging.error
            flash(f'Error processing CSV file: {str(e)}', 'danger')
            
    else:
        print(f"--- DEBUG: File format check failed for {file.filename} ---")
        flash('Invalid file format. Please upload a .csv file.', 'danger')
            
    print("--- DEBUG: Reaching end of /upload_csv route ---")
    # Redirect back to the index page, focusing on the waitlist table after upload attempt
    return redirect(url_for('index') + '#waitlist-table') # Added fragment

@app.route('/providers', methods=['GET'])
def list_providers():
    providers = provider_manager.get_provider_list()
    return render_template('providers.html', providers=providers)

@app.route('/providers/add', methods=['POST'])
def add_provider():
    first_name = request.form.get('first_name')
    last_initial = request.form.get('last_initial')
    
    if first_name:
        # Call add_provider without is_active
        success = provider_manager.add_provider(first_name, last_initial)
        if success:
            flash('Provider added successfully', 'success')
        else:
            flash('Provider already exists', 'danger')
    else:
        flash('First name is required', 'danger')
        
    # Redirect back to providers list
    return redirect(url_for('list_providers') + '#provider-list') # Added fragment

@app.route('/providers/remove', methods=['POST'])
def remove_provider():
    first_name = request.form.get('first_name')
    last_initial = request.form.get('last_initial')
    
    if provider_manager.remove_provider(first_name, last_initial):
        flash('Provider removed successfully')
    else:
        flash('Provider not found')
        
    # Redirect back to providers list
    return redirect(url_for('list_providers') + '#provider-list') # Added fragment

@app.route('/providers/upload_csv', methods=['POST'])
def upload_providers_csv():
    if 'provider_csv' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('list_providers'))
    
    file = request.files['provider_csv']
    
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('list_providers'))
    
    if file and file.filename.endswith('.csv'):
        try:
            # Process the uploaded CSV
            stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
            # Expecting only 'name' column, handle potential extra columns gracefully
            reader = csv.DictReader(stream) # Let DictReader determine headers

            count = 0
            added_names = set() # Keep track of names added in this upload

            for row in reader:
                 provider_name_raw = row.get('name', '').strip()
                 if provider_name_raw:
                    # Simple split assuming "First LastInitial" format if space exists
                    name_parts = provider_name_raw.split(maxsplit=1)
                    first_name = name_parts[0]
                    last_initial = name_parts[1] if len(name_parts) > 1 else None

                    # Construct the name as the manager expects for checking
                    full_name_check = first_name
                    if last_initial:
                        full_name_check += f" {last_initial}"

                    # Check if already added in this batch to avoid duplicate messages
                    if full_name_check.lower() not in added_names:
                         # Call add_provider without is_active
                        if provider_manager.add_provider(first_name, last_initial):
                            count += 1
                            added_names.add(full_name_check.lower()) # Add to set after successful add


            if count > 0:
                flash(f'Successfully added {count} new providers', 'success')
            else:
                flash('No new providers were added (duplicates or empty names skipped)', 'info')

        except Exception as e:
             logging.error(f"Error processing provider CSV: {e}", exc_info=True)
             flash(f'Error processing CSV: {str(e)}', 'danger')

    # Redirect back to providers list
    return redirect(url_for('list_providers') + '#provider-list') # Added fragment

@app.route('/cancelled_appointments', methods=['GET'])
def list_cancelled_appointments():
    all_providers = provider_manager.get_provider_list()
    current_slots = slot_manager.get_all_slots() # Slots now include 'slot_period'
    current_slots.sort(key=lambda s: s.get('slot_date') or date.min, reverse=True)

    return render_template('cancelled_appointments.html',
                          providers=all_providers,
                          cancelled_appointments=current_slots,
                          eligible_patients=None,
                          current_appointment=None)

# This route uses the manager's add_slot, which now requires slot_period
@app.route('/create_slot_and_find_matches', methods=['POST'])
def create_slot_and_find_matches():
    provider = request.form.get('provider')
    duration = request.form.get('duration')
    slot_date_str = request.form.get('slot_date')
    slot_period = request.form.get('slot_period') # Get AM/PM
    notes = request.form.get('notes', '')

    slot_date_obj = None
    if slot_date_str:
        try:
            slot_date_obj = date.fromisoformat(slot_date_str)
        except ValueError:
            flash('Invalid date format provided. Please use YYYY-MM-DD.', 'danger')
            return redirect(url_for('list_cancelled_appointments') + '#add-slot-form')
    else:
        flash('Date is required.', 'danger')
        return redirect(url_for('list_cancelled_appointments') + '#add-slot-form')

    # Validate required fields including slot_period
    if not provider or not duration or not slot_period:
        flash('Please select Provider, Duration, Date, and Time (AM/PM).', 'warning')
        return redirect(url_for('list_cancelled_appointments') + '#add-slot-form')

    # 1. Create the slot using the manager (pass slot_period)
    new_appointment = slot_manager.add_slot(
        provider=provider,
        duration=duration,
        slot_date=slot_date_obj,
        slot_period=slot_period, # Pass AM/PM
        notes=notes
    )
    if not new_appointment:
         # Manager logs error if period was invalid
         flash('Failed to create appointment slot (invalid period or other error).', 'danger')
         return redirect(url_for('list_cancelled_appointments'))

    logging.debug(f"Created and saved new cancelled slot via manager: {new_appointment.get('id')}")

    # 2. Find eligible patients for this *new* slot using the helper
    eligible_patients = find_eligible_patients(new_appointment) # Pass the dict

    # Get data for rendering the template
    all_providers = provider_manager.get_provider_list()
    current_slots = slot_manager.get_all_slots()
    current_slots.sort(key=lambda s: s.get('slot_date') or date.min, reverse=True)

    return render_template('cancelled_appointments.html',
                           providers=all_providers,
                           cancelled_appointments=current_slots,
                           eligible_patients=eligible_patients,
                           current_appointment=new_appointment,
                           focus_element_id='eligible-patients-list' if eligible_patients else 'add-slot-form')

# This route uses the manager's add_slot, which now requires slot_period
@app.route('/add_cancelled_appointment', methods=['POST'])
def add_cancelled_appointment():
    provider = request.form.get('provider')
    duration = request.form.get('duration')
    slot_date_str = request.form.get('slot_date')
    slot_period = request.form.get('slot_period') # Get AM/PM
    notes = request.form.get('notes', '')

    slot_date_obj = None
    if slot_date_str:
        try:
            slot_date_obj = date.fromisoformat(slot_date_str)
        except ValueError:
            flash('Invalid date format provided. Please use YYYY-MM-DD.', 'danger')
            return redirect(url_for('list_cancelled_appointments') + '#add-slot-form')
    else:
        flash('Date is required.', 'danger')
        return redirect(url_for('list_cancelled_appointments') + '#add-slot-form')

    # Validate required fields including slot_period
    if not provider or not duration or not slot_period:
        flash('Provider, Duration, Date, and Time (AM/PM) are required', 'danger')
        return redirect(url_for('list_cancelled_appointments') + '#add-slot-form')

    # Create appointment object using the manager (pass slot_period)
    appointment = slot_manager.add_slot(provider, duration, slot_date_obj, slot_period, notes)

    if not appointment:
        # Manager logs error if period was invalid
        flash('Failed to create appointment slot (invalid period or other error).', 'danger')
        return redirect(url_for('list_cancelled_appointments'))

    # Find eligible patients using the helper
    eligible_patients = find_eligible_patients(appointment)

    # --- Logging ---
    logging.debug(f"Rendering cancelled_appointments template from add_cancelled_appointment.")
    logging.debug(f"Current appointment ID: {appointment.get('id')}, Date: {appointment.get('slot_date')}, Period: {appointment.get('slot_period')}") # Log period
    # ... (rest of logging unchanged) ...

    # Get data for rendering
    current_slots = slot_manager.get_all_slots()
    current_slots.sort(key=lambda s: s.get('slot_date') or date.min, reverse=True)
    all_providers = provider_manager.get_provider_list()

    return render_template('cancelled_appointments.html',
                          providers=all_providers,
                          cancelled_appointments=current_slots,
                          eligible_patients=eligible_patients,
                          current_appointment=appointment,
                          focus_element_id='eligible-patients-list' if eligible_patients else 'add-slot-form')

# This route finds matches using the helper, which now uses the manager's updated logic
@app.route('/find_matches_for_appointment/<appointment_id>', methods=['POST'])
def find_matches_for_appointment(appointment_id):
    appointment = slot_manager.get_slot_by_id(appointment_id) # Includes period

    if not appointment:
        flash('Appointment not found', 'danger')
        return redirect(url_for('list_cancelled_appointments') + '#cancelled-slots-list')

    if appointment.get('matched_patient'):
        flash('This appointment is already matched.', 'info')
        return redirect(url_for('list_cancelled_appointments') + '#cancelled-slots-list')

    # Find eligible patients using the helper (which calls manager's updated method)
    eligible_patients = find_eligible_patients(appointment)

    # --- Logging ---
    logging.debug(f"Rendering cancelled_appointments template from find_matches_for_appointment.")
    logging.debug(f"Current appointment ID: {appointment.get('id')}, Date: {appointment.get('slot_date')}, Period: {appointment.get('slot_period')}") # Log period
    # ... (rest of logging unchanged) ...

    # Get data for rendering
    current_slots = slot_manager.get_all_slots()
    current_slots.sort(key=lambda s: s.get('slot_date') or date.min, reverse=True)
    all_providers = provider_manager.get_provider_list()

    return render_template('cancelled_appointments.html',
                        providers=all_providers,
                        cancelled_appointments=current_slots,
                        eligible_patients=eligible_patients,
                        current_appointment=appointment,
                        focus_element_id='eligible-patients-list' if eligible_patients else f'slot-{appointment_id}')

@app.route('/assign_appointment/<patient_id>/<appointment_id>', methods=['POST'], strict_slashes=False)
def assign_appointment(patient_id, appointment_id):
    """Assign a patient to a cancelled appointment slot and remove the slot."""
    logging.debug(f"Entering assign_appointment for patient_id={patient_id}, appointment_id={appointment_id}")
    # Update wait times first (may not be strictly needed here but harmless)
    waitlist_manager.update_wait_times()

    # Find the patient
    patient = waitlist_manager.get_patient_by_id(patient_id) # Assuming manager has/will have this method

    if not patient: # Check if patient exists
        flash('Patient not found on waitlist.', 'danger')
        logging.warning(f"Assign appointment: Patient ID {patient_id} not found.")
        # Redirect back to the main waitlist page if patient not found
        return redirect(url_for('index') + '#waitlist-table')

    # Find the appointment using the manager
    appointment = slot_manager.get_slot_by_id(appointment_id)

    if not appointment:
        flash('Appointment slot not found.', 'danger')
        logging.warning(f"Assign appointment: Slot ID {appointment_id} not found.")
        # Redirect back to the main waitlist page if slot not found
        return redirect(url_for('index') + '#waitlist-table')

    # Check if slot already matched (Although we're removing, this check prevents issues if clicked twice)
    if appointment.get('matched_patient'):
        flash(f'Slot already assigned to {appointment["matched_patient"].get("name", "another patient")}. Refreshing list.', 'warning')
        logging.debug(f"Assign appointment: Slot {appointment_id} was already matched. Preventing removal.")
        # Redirect back to the main waitlist page if already matched
        return redirect(url_for('index') + '#waitlist-table')

    # --- Eligibility Check using Helper ---
    # Re-check eligibility based on potentially updated patient/slot data
    # We will reuse the filtering logic from propose_slots implicitly by checking if the assignment works
    # Note: Direct eligibility check like in propose_slots could be added here for extra safety,
    # but the core logic relies on finding the patient/slot and removing them.

    # Attempt to remove patient from waitlist FIRST
    try:
        logging.debug(f"Attempting to remove patient ID: {patient_id} from waitlist.")
        patient_removed = waitlist_manager.remove_patient(patient_id)
        logging.debug(f"Patient removal result: {patient_removed}")

        if patient_removed:
            # If patient removal was successful, THEN REMOVE the cancelled slot
            logging.debug(f"Patient {patient_id} removed from waitlist. Attempting to remove cancelled slot ID: {appointment_id}")
            slot_removed = slot_manager.remove_slot(appointment_id) # Use remove_slot instead of assign

            if slot_removed:
                flash(f'Successfully assigned {patient.get("name", "Unknown Patient")} to the appointment time. Patient removed from waitlist and slot removed from cancelled list.', 'success')
                # --- MODIFIED REDIRECT ---
                target_url = url_for('index') + '#waitlist-table' # Go to waitlist top after success
                # --- END MODIFIED REDIRECT ---
                logging.debug(f"Patient {patient_id} removed from waitlist and slot {appointment_id} removed successfully. Redirecting to: {target_url}")
                # --- Save Backup After Successful Assignment/Removal ---
                waitlist_manager.save_backup()
                # slot_manager.remove_slot() handles its own save
                # --- End Save Backup ---
                return redirect(target_url)
            else:
                # This case means patient was removed but slot removal failed (e.g., slot disappeared between checks)
                # CRITICAL: Need to add patient back or handle this state
                flash('Patient removed from waitlist, but failed to REMOVE slot (it may have been removed by another process). Please manually verify patient status and slot list.', 'danger')
                logging.error(f"Removed patient {patient_id} but failed to REMOVE slot {appointment_id}. Patient needs manual re-addition or verification.")
                # Consider adding the patient back here if possible, or provide clearer instructions
                # Redirect back to waitlist
                return redirect(url_for('index') + '#waitlist-table')

        else:
            # Patient removal failed (e.g., patient wasn't actually on waitlist anymore)
            flash('Failed to remove patient from waitlist (they may have already been scheduled or removed). Slot removal cancelled.', 'danger')
            logging.debug(f"Patient removal failed for ID {patient_id}, slot removal cancelled, redirecting")
            # Redirect back to waitlist
            return redirect(url_for('index') + '#waitlist-table')
    except Exception as e:
        logging.error(f"Exception during patient removal or slot removal: {e}", exc_info=True)
        flash('An unexpected error occurred while assigning the patient and removing the slot.', 'danger')
        # Redirect back to waitlist
        return redirect(url_for('index') + '#waitlist-table')

def find_eligible_patients(cancelled_appointment: dict) -> list:
    """
    Finds eligible patients for a cancelled slot by calling the waitlist manager.
    Uses the manager's logic for filtering (provider, duration, day, period) and sorting.
    """
    provider_name = cancelled_appointment.get('provider')
    slot_duration = cancelled_appointment.get('duration')
    slot_day_of_week = cancelled_appointment.get('slot_day_of_week')
    slot_period = cancelled_appointment.get('slot_period') # Get AM/PM from slot

    # Essential info check now includes slot_period
    if not provider_name or not slot_duration or not slot_day_of_week or not slot_period:
        logging.error(f"Cannot find eligible patients: Missing essential info in cancelled_appointment dict: {cancelled_appointment}")
        return []

    # Call the waitlist manager's method, passing the period
    eligible_patients = waitlist_manager.find_eligible_patients(
        provider_name,
        str(slot_duration),
        slot_day_of_week,
        slot_period # Pass the period
    )

    logging.debug(f"Found {len(eligible_patients)} eligible patients via manager for slot {cancelled_appointment.get('id')} on {slot_day_of_week} {slot_period}")
    return eligible_patients

@app.route('/remove_cancelled_slot/<appointment_id>', methods=['POST'])
def remove_cancelled_slot(appointment_id):
    """Removes a specific cancelled appointment slot using the manager."""
    # Use the manager's remove method
    removed = slot_manager.remove_slot(appointment_id)

    if removed:
        flash('Cancelled appointment slot removed successfully.', 'success')
        logging.debug(f"Removed cancelled slot ID: {appointment_id} via manager")
    else:
        # Manager already logs warnings for non-existent IDs
        flash('Cancelled appointment slot not found or already removed.', 'warning')

    # Redirect back to the list
    return redirect(url_for('list_cancelled_appointments') + '#cancelled-slots-list') # Added fragment

@app.route('/edit_cancelled_slot/<appointment_id>', methods=['GET'])
def edit_cancelled_slot(appointment_id):
    """Shows the form to edit a cancelled appointment slot."""
    appointment_to_edit = slot_manager.get_slot_by_id(appointment_id) # Includes period

    if not appointment_to_edit:
        flash('Cancelled appointment slot not found.', 'danger')
        return redirect(url_for('list_cancelled_appointments') + '#cancelled-slots-list')

    if appointment_to_edit.get('matched_patient'):
        flash('Cannot edit a slot that is already matched.', 'warning')
        return redirect(url_for('list_cancelled_appointments') + '#cancelled-slots-list')

    all_providers = provider_manager.get_provider_list()
    # Pass the full slot dict (including period) to the template
    return render_template('edit_cancelled_slot.html',
                           appointment=appointment_to_edit,
                           providers=all_providers)

@app.route('/update_cancelled_slot/<appointment_id>', methods=['POST'])
def update_cancelled_slot(appointment_id):
    """Updates the details (including date and period) of a cancelled slot."""
    appointment_to_update = slot_manager.get_slot_by_id(appointment_id)

    if not appointment_to_update:
        flash('Cancelled appointment slot not found.', 'danger')
        return redirect(url_for('list_cancelled_appointments') + '#cancelled-slots-list')

    if appointment_to_update.get('matched_patient'):
         flash('Cannot edit a slot that is already matched.', 'warning')
         return redirect(url_for('list_cancelled_appointments') + '#cancelled-slots-list')

    # Get updated data from form
    provider = request.form.get('provider')
    duration = request.form.get('duration')
    slot_date_str = request.form.get('slot_date')
    slot_period = request.form.get('slot_period') # Get AM/PM
    notes = request.form.get('notes', '')

    slot_date_obj = None
    if slot_date_str:
        try:
            slot_date_obj = date.fromisoformat(slot_date_str)
        except ValueError:
            flash('Invalid date format provided. Please use YYYY-MM-DD.', 'danger')
            all_providers = provider_manager.get_provider_list()
            return render_template('edit_cancelled_slot.html',
                                   appointment=appointment_to_update,
                                   providers=all_providers)
    else:
        flash('Date is required.', 'danger')
        all_providers = provider_manager.get_provider_list()
        return render_template('edit_cancelled_slot.html',
                               appointment=appointment_to_update,
                               providers=all_providers)

    # Basic validation including period
    if not provider or not duration or not slot_period:
        flash('Provider, Duration, Date, and Time (AM/PM) are required.', 'danger')
        all_providers = provider_manager.get_provider_list()
        return render_template('edit_cancelled_slot.html',
                               appointment=appointment_to_update,
                               providers=all_providers)

    # Update using the manager (pass slot_period)
    updated = slot_manager.update_slot(
        appointment_id,
        provider,
        duration,
        slot_date_obj,
        slot_period, # Pass AM/PM
        notes
    )

    if updated:
        flash('Cancelled appointment slot updated successfully.', 'success')
        logging.debug(f"Updated cancelled slot ID: {appointment_id} via manager")
    else:
        # Manager handles logging, flash error if update failed (e.g., invalid period)
        flash('Failed to update cancelled appointment slot (invalid period, removed, or matched).', 'danger')

    return redirect(url_for('list_cancelled_appointments') + '#cancelled-slots-list')

# --- Add New Route for Proposing Slots ---
@app.route('/propose_slots/<patient_id>', methods=['GET'])
def propose_slots(patient_id):
    logging.debug(f"Entering propose_slots for patient_id={patient_id}")
    patient = waitlist_manager.get_patient_by_id(patient_id) # Patient data includes 'availability' dict and 'availability_mode'

    if not patient:
        flash('Patient not found.', 'danger')
        return redirect(url_for('index') + '#waitlist-table')

    if patient.get('status') != 'waiting':
        flash(f'{patient.get("name", "Patient")} is not currently waiting.', 'info')
        return redirect(url_for('index') + '#waitlist-table')

    # Get available slots (including 'slot_period')
    all_slots = slot_manager.get_all_slots()
    available_slots = [s for s in all_slots if s.get('matched_patient') is None and s.get('slot_period')] # Ensure slot has period
    logging.debug(f"Found {len(available_slots)} available slots with defined period initially.")

    # Filter available slots based on patient requirements (including mode)
    matching_slots = []
    patient_duration = str(patient.get('duration', ''))
    patient_provider_pref = patient.get('provider', '').strip().lower()
    patient_availability_prefs = patient.get('availability', {})
    patient_mode = patient.get('availability_mode', 'available')
    has_patient_preferences = bool(patient_availability_prefs)

    logging.debug(f"Filtering slots for Patient {patient_id} (Mode: {patient_mode}, Prefs: {patient_availability_prefs})")

    for slot in available_slots:
        slot_duration = str(slot.get('duration', ''))
        slot_provider = slot.get('provider', '').strip().lower()
        slot_day_raw = slot.get('slot_day_of_week')
        slot_day = slot_day_raw.strip().lower() if slot_day_raw else None
        slot_period_raw = slot.get('slot_period')
        slot_period = slot_period_raw.strip().upper() if slot_period_raw else None

        # Ensure slot has necessary info for matching
        if not slot_day or not slot_period:
            logging.debug(f"Slot {slot.get('id')} skipped: Missing day or period.")
            continue

        # 1. Check Duration
        if patient_duration != slot_duration:
            logging.debug(f"Slot {slot.get('id')} skipped: Duration mismatch (Patient: {patient_duration}, Slot: {slot_duration})")
            continue

        # 2. Check Provider
        provider_ok = (patient_provider_pref == 'no preference' or patient_provider_pref == slot_provider)
        if not provider_ok:
            logging.debug(f"Slot {slot.get('id')} skipped: Provider mismatch (Patient: {patient_provider_pref}, Slot: {slot_provider})")
            continue

        # 3. Check Day/Time Availability (incorporating mode)
        is_available_for_slot = True # Start assuming available

        # Check if the specific slot day/time matches a preference
        slot_matches_preference = False
        if slot_day in patient_availability_prefs:
            day_prefs = patient_availability_prefs.get(slot_day, [])
            day_prefs_upper = [p.strip().upper() for p in day_prefs]
            if slot_period in day_prefs_upper or ('AM' in day_prefs_upper and 'PM' in day_prefs_upper):
                slot_matches_preference = True

        # Apply mode logic:
        if patient_mode == 'available':
            # Available Mode: Must match pref OR have no prefs listed
            if has_patient_preferences and not slot_matches_preference:
                is_available_for_slot = False
                logging.debug(f"Slot {slot.get('id')} skipped: Patient mode 'available', has prefs, but slot doesn't match.")
        elif patient_mode == 'unavailable':
            # Unavailable Mode: Must NOT match a listed preference
            if has_patient_preferences and slot_matches_preference:
                is_available_for_slot = False
                logging.debug(f"Slot {slot.get('id')} skipped: Patient mode 'unavailable', has prefs, and slot matches unavailable time.")

        if not is_available_for_slot:
            continue # Skip if determined unavailable

        # If all checks pass, add to matching slots
        logging.debug(f"Slot {slot.get('id')} is a match for patient {patient_id}.")
        matching_slots.append(slot)

    # Sort matching slots by date
    matching_slots.sort(key=lambda s: s.get('slot_date') or date.min)

    logging.debug(f"Found {len(matching_slots)} matching slots for patient {patient_id}.")
    return render_template('propose_slots.html', patient=patient, matching_slots=matching_slots)
# --- End New Route ---

if __name__ == '__main__':
    # Ensure provider.csv exists (even if empty) - Handled by ProviderManager init now

    # Load initial data before starting the server - Handled by manager init

    # --- Add this line to print the URL map ---
    print("--- Registered URL Routes ---")
    print(app.url_map)
    print("--- End Registered URL Routes ---")
    # --- End added line ---

    print("Starting Flask application...")
    app.run(debug=True, host="0.0.0.0", port=7776)
