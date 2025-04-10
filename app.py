from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime, timedelta
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
        
        # Get all providers (not just active ones)
        all_providers = provider_manager.get_provider_list()
        active_providers = provider_manager.get_active_providers()
        
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
                is_emergency = x.get('appointment_type', '').lower() == 'emergency'
                # Sort order: Scheduled (True) last, Emergency (False means emergency comes first) first, then by wait time
                return (is_scheduled, not is_emergency, wait_minutes)
            except Exception as e:
                logging.error(f"Error calculating sort key for patient {x.get('id')}: {e}", exc_info=True)
                return (True, True, 0) # Default sort value on error

        sorted_waitlist = sorted(waitlist, key=sort_key_safe)
        
        # Show a different message if there are providers but they're all inactive
        if not has_providers:
            flash('Please upload a list of Provider names to proceed', 'warning')
        elif not active_providers:
            flash('All providers are currently marked as inactive. Please activate at least one provider.', 'warning')
        
        logging.debug("Index route: Rendering index.html")
        return render_template('index.html', 
                              waitlist=sorted_waitlist, 
                              providers=active_providers,
                              has_providers=has_providers)
    except Exception as e:
        logging.error(f"Exception in index route: {e}", exc_info=True)
        flash('An error occurred while loading the main page.', 'danger')
        # Render a simpler template or redirect to an error page if possible
        # For now, just return a simple error message
        return "<h1>An error occurred</h1><p>Please check the server logs.</p>", 500

@app.route('/add_patient', methods=['POST'])
def add_patient():
    name = request.form.get('name')
    phone = request.form.get('phone')
    email = request.form.get('email')
    reason = request.form.get('reason')
    urgency = request.form.get('urgency')
    appointment_type = request.form.get('appointment_type')
    duration = request.form.get('duration')
    provider = request.form.get('provider')
    
    if name and phone:  # Basic validation
        # Use the waitlist manager to add the patient
        waitlist_manager.add_patient(
            name=name,
            phone=phone,
            email=email,
            reason=reason,
            urgency=urgency,
            appointment_type=appointment_type,
            duration=duration,
            provider=provider
        )
    
    return redirect(url_for('index'))

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
    return redirect(url_for('index'))

# Update the remove_patient route
@app.route('/remove_patient/<patient_id>', methods=['POST'])
def remove_patient(patient_id):
    if waitlist_manager.remove_patient(patient_id):
        flash('Patient removed successfully.', 'success')
    else:
        flash('Failed to remove patient.', 'danger')
    return redirect(url_for('index'))

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
    return redirect(url_for('index'))
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
    valid_providers = ['no preference'] + [p['name'].lower() for p in provider_manager.get_provider_list()]
    
    # Convert empty string or None to 'no preference'
    if not value or value.lower() == 'no preference':
        return 'no preference'
    
    # Check if the provided value is in our list (case-insensitive)
    for provider in valid_providers:
        if provider == value.lower():
            # Return the correctly cased name from the manager if possible
            for p_dict in provider_manager.get_provider_list():
                if p_dict['name'].lower() == provider:
                    return p_dict['name']
            return provider # Fallback to lowercased if not found (shouldn't happen)
    
    # Default to 'no preference' if not found
    return 'no preference'

def validate_urgency(value):
    valid_urgency = ['low', 'medium', 'high']
    return value.lower() if value.lower() in valid_urgency else 'medium'

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    print("--- DEBUG: /upload_csv route hit ---")
    # Check if we have providers
    if not provider_manager.get_active_providers():
        print("--- DEBUG: No active providers found ---")
        flash('Please add providers before uploading patient data', 'warning')
        return redirect(url_for('index'))
    
    print("--- DEBUG: Active providers check passed ---")
    if 'csv_file' not in request.files:
        print("--- DEBUG: 'csv_file' not in request.files ---")
        flash('No file selected for upload.', 'warning')
        return redirect(url_for('index'))
    
    file = request.files['csv_file']
    print(f"--- DEBUG: File found: {file.filename} ---")
    if file.filename == '':
        print("--- DEBUG: File filename is empty ---")
        flash('No file selected for upload.', 'warning')
        return redirect(url_for('index'))

    if file and file.filename.endswith('.csv'):
        print("--- DEBUG: File format check passed ---")
        try:
            print("--- DEBUG: Entering try block for CSV processing ---")
            stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
            # Use pandas or csv reader
            # Using csv.DictReader for consistency with manager
            reader = csv.DictReader(stream)
            added_count = 0
            skipped_count = 0 # Added counter for skipped duplicates
            required_columns = ['name', 'phone'] # Example required

            # --- Get existing patients for duplicate check ---
            existing_patients_list = waitlist_manager.get_all_patients()
            existing_patients_set = {(p.get('name', '').strip(), p.get('phone', '').strip()) 
                                     for p in existing_patients_list if p.get('name') and p.get('phone')} 
            print(f"--- DEBUG: Found {len(existing_patients_set)} existing patients for duplicate check ---")
            # --- End duplicate check setup ---

            patients_to_add = []
            headers = reader.fieldnames
            print(f"--- DEBUG: CSV Headers: {headers} ---") # Added print
            if not all(col in headers for col in required_columns):
                 print(f"--- DEBUG: Missing required columns ({required_columns}) ---") # Added print
                 flash(f'CSV must contain at least {", ".join(required_columns)} columns', 'danger')
                 return redirect(url_for('index')) # Corrected return placement

            print("--- DEBUG: Required columns check passed ---") # Added print
            first_row_processed = False # Added flag
            for row in reader:
                 # --- Duplicate Check ---
                 csv_name = row.get('name', '').strip()
                 csv_phone = row.get('phone', '').strip()
                 if not csv_name or not csv_phone: # Skip rows with missing name or phone
                     print(f"--- DEBUG: Skipping row due to missing name/phone: {row} ---")
                     skipped_count += 1
                     continue 
                 if (csv_name, csv_phone) in existing_patients_set:
                     print(f"--- DEBUG: Skipping duplicate patient: {csv_name}, {csv_phone} ---")
                     skipped_count += 1
                     continue
                 # --- End Duplicate Check ---

                 if not first_row_processed: # Added conditional print
                     print(f"--- DEBUG: Processing first row: {row} ---")
                     first_row_processed = True
                 # Use correct provider column name ('provider' vs 'provider')
                 provider_value = row.get('provider') or row.get('provider', '') # Use 'provider' consistently

                 # --- Try parsing the timestamp ---
                 datetime_str = row.get('date_time_entered', '').strip()
                 parsed_timestamp = None
                 if datetime_str:
                     # Add %# format for potential missing leading zeros on Windows
                     possible_formats = [
                         '%m/%d/%Y %H:%M:%S',    # Standard MM/DD/YYYY HH:MM:SS
                         '%#m/%#d/%Y %#H:%M:%S', # Attempt M/D/YYYY H:MM:SS (Windows?)
                         '%m/%d/%y %I:%M %p',    # MM/DD/YY HH:MM AM/PM
                         '%m/%d/%Y %I:%M %p'     # MM/DD/YYYY HH:MM AM/PM
                     ]
                     # First, try ISO format
                     try:
                         parsed_timestamp = datetime.fromisoformat(datetime_str)
                     except ValueError:
                         # If ISO fails, try other formats
                         for fmt in possible_formats:
                             try:
                                 parsed_timestamp = datetime.strptime(datetime_str, fmt)
                                 break # Stop trying formats if one works
                             except ValueError:
                                 continue # Try next format

                     if not parsed_timestamp:
                         # Updated print statement to reflect ISO attempt
                         print(f"--- DEBUG: Could not parse timestamp '{datetime_str}' for patient {row.get('name')} using ISO or formats {possible_formats} ---")
                 # --- End timestamp parsing ---

                 # Add data for non-duplicate patient
                 patients_to_add.append({
                    'name': csv_name, # Use stripped name
                    'phone': csv_phone, # Use stripped phone
                    'email': row.get('email', ''),
                    'reason': row.get('reason', ''),
                    'urgency': validate_urgency(row.get('urgency', 'medium')),
                    'appointment_type': validate_appointment_type(row.get('appointment_type')),
                    'duration': validate_duration(row.get('duration', '30')),
                    'provider': validate_provider(provider_value), # Use combined value
                    'timestamp': parsed_timestamp # Add parsed timestamp here
                 })
                 added_count += 1
                 # Add to existing set immediately to prevent duplicates *within* the CSV
                 existing_patients_set.add((csv_name, csv_phone)) 
            
            print(f"--- DEBUG: Finished reading rows. Added: {added_count}, Skipped: {skipped_count} ---") 

            # Now add all collected patients (manager handles appending internally)
            if patients_to_add:
                print(f"--- DEBUG: Adding {len(patients_to_add)} new patients to manager ---") 
                for p_data in patients_to_add:
                    # Extract timestamp before passing the rest as kwargs
                    patient_timestamp = p_data.pop('timestamp', None) 
                    # This appends to self.patients in the manager
                    waitlist_manager.add_patient(timestamp=patient_timestamp, **p_data) # Pass timestamp separately

            print("--- DEBUG: Finished adding patients to manager ---")
            # --- Update Flash Message ---
            if added_count > 0 and skipped_count > 0:
                flash(f'Successfully added {added_count} new patients. Skipped {skipped_count} duplicates or rows with missing info.', 'success')
            elif added_count > 0:
                flash(f'Successfully added {added_count} new patients from CSV.', 'success')
            elif skipped_count > 0:
                flash(f'No new patients added. Skipped {skipped_count} duplicates or rows with missing info.', 'info')
            else:
                flash('No patients added from CSV.', 'info')
            # --- End Flash Message Update ---

        except Exception as e:
            print(f"--- DEBUG: Exception caught in /upload_csv: {str(e)} ---") # Added print
            print(f"Error processing patient CSV: {str(e)}")
            flash(f'Error processing CSV file: {str(e)}', 'danger')
            
    else:
        print(f"--- DEBUG: File format check failed for {file.filename} ---")
        flash('Invalid file format. Please upload a .csv file.', 'danger')
            
    print("--- DEBUG: Reaching end of /upload_csv route ---")
    return redirect(url_for('index'))

@app.route('/providers', methods=['GET'])
def list_providers():
    providers = provider_manager.get_provider_list()
    return render_template('providers.html', providers=providers)

@app.route('/providers/add', methods=['POST'])
def add_provider():
    first_name = request.form.get('first_name')
    last_initial = request.form.get('last_initial')
    
    if first_name:
        # Set is_active to True by default
        success = provider_manager.add_provider(first_name, last_initial, is_active=True)
        if success:
            flash('Provider added successfully', 'success')
        else:
            flash('Provider already exists', 'danger')
    else:
        flash('First name is required', 'danger')
        
    return redirect(url_for('list_providers'))

@app.route('/providers/remove', methods=['POST'])
def remove_provider():
    first_name = request.form.get('first_name')
    last_initial = request.form.get('last_initial')
    
    if provider_manager.remove_provider(first_name, last_initial):
        flash('Provider removed successfully')
    else:
        flash('Provider not found')
        
    return redirect(url_for('list_providers'))

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
            csv_data = csv.reader(stream)
            
            # Skip header row if exists
            header = next(csv_data, None)
            
            count = 0
            for row in csv_data:
                if len(row) >= 1 and row[0].strip():
                    # Format: name, is_active (optional)
                    name_parts = row[0].strip().split()
                    first_name = name_parts[0]
                    last_initial = name_parts[1] if len(name_parts) > 1 else None
                    
                    # Set is_active to True by default if not specified
                    is_active = True
                    if len(row) >= 2:
                        is_active = row[1].lower() in ['true', 'yes', '1', 'y', 't']
                    
                    if provider_manager.add_provider(first_name, last_initial, is_active):
                        count += 1
            
            if count > 0:
                flash(f'Successfully added {count} providers', 'success')
            else:
                flash('No new providers were added', 'info')
                
        except Exception as e:
            flash(f'Error processing CSV: {str(e)}', 'danger')
    
    return redirect(url_for('list_providers'))

@app.route('/providers/toggle_active/<provider_name>', methods=['POST'])
def toggle_provider_active(provider_name):
    success = provider_manager.toggle_provider_active(provider_name)
    if success:
        flash(f'Provider status updated successfully', 'success')
    else:
        flash('Provider not found', 'danger')
    return redirect(url_for('list_providers'))

@app.route('/cancelled_appointments', methods=['GET'])
def list_cancelled_appointments():
    # Update wait times first
    waitlist_manager.update_wait_times()

    # Get all providers
    providers = provider_manager.get_provider_list()
    # Get slots from the manager
    current_slots = slot_manager.get_all_slots()

    return render_template('cancelled_appointments.html',
                          providers=providers,
                          cancelled_appointments=current_slots, # Use data from manager
                          eligible_patients=None,
                          current_appointment=None)

@app.route('/create_slot_and_find_matches', methods=['POST'])
def create_slot_and_find_matches():
    """Creates a cancelled slot using the manager and finds matches."""
    provider = request.form.get('provider')
    duration = request.form.get('duration')

    if not provider or not duration:
        flash('Please select both a provider and a duration.', 'warning')
        return redirect(url_for('index'))

    # 1. Create the slot using the manager
    new_appointment = slot_manager.add_slot(
        provider=provider,
        duration=duration
    )
    logging.debug(f"Created and saved new cancelled slot via manager: {new_appointment.get('id')}")

    # 2. Find eligible patients for this *new* slot
    eligible_patients = find_eligible_patients(new_appointment) # Pass the dict returned by manager

    # Get providers for rendering the target template
    providers = provider_manager.get_provider_list()
    # Get all current slots from manager for the list display
    current_slots = slot_manager.get_all_slots()

    # 3. Render the template
    return render_template('cancelled_appointments.html',
                           providers=providers,
                           cancelled_appointments=current_slots, # Pass the updated list from manager
                           eligible_patients=eligible_patients,
                           current_appointment=new_appointment, # Pass the newly created slot dict
                           is_temporary_search=False)

@app.route('/add_cancelled_appointment', methods=['POST'])
def add_cancelled_appointment():
    provider = request.form.get('provider')
    duration = request.form.get('duration')
    notes = request.form.get('notes', '')

    if not provider or not duration:
        flash('Please fill in all required fields', 'danger')
        return redirect(url_for('list_cancelled_appointments'))

    # Create appointment object using the manager
    appointment = slot_manager.add_slot(provider, duration, notes)

    # Find eligible patients for this appointment
    eligible_patients = find_eligible_patients(appointment)

    # --- Logging ---
    logging.debug(f"Rendering cancelled_appointments template from add_cancelled_appointment.")
    logging.debug(f"Current appointment ID: {appointment.get('id')}")
    if not appointment.get('id'):
         logging.error("!!! CRITICAL: appointment['id'] is missing after adding via manager in add_cancelled_appointment !!!")
    # --- End Logging ---

    # Get all slots for rendering
    current_slots = slot_manager.get_all_slots()

    # Render template with eligible patients
    return render_template('cancelled_appointments.html',
                          providers=provider_manager.get_provider_list(),
                          cancelled_appointments=current_slots, # Use list from manager
                          eligible_patients=eligible_patients,
                          current_appointment=appointment,
                          is_temporary_search=False)

@app.route('/find_matches_for_appointment/<appointment_id>', methods=['POST'])
def find_matches_for_appointment(appointment_id):
    # Find the appointment using the manager
    appointment = slot_manager.get_slot_by_id(appointment_id)

    if not appointment:
        flash('Appointment not found', 'danger')
        return redirect(url_for('list_cancelled_appointments'))

    # If already matched, show info message
    if appointment.get('matched_patient'):
        flash('This appointment is already matched with a patient', 'info')
        return redirect(url_for('list_cancelled_appointments'))

    # Find eligible patients
    eligible_patients = find_eligible_patients(appointment)

    # --- Logging ---
    logging.debug(f"Rendering cancelled_appointments template from find_matches_for_appointment.")
    logging.debug(f"Current appointment ID: {appointment.get('id')}")
    if not appointment.get('id'):
         logging.error("!!! CRITICAL: appointment['id'] is missing after getting from manager in find_matches_for_appointment !!!")
    # --- End Logging ---

    # Get all slots for rendering
    current_slots = slot_manager.get_all_slots()

    # Render template with eligible patients
    return render_template('cancelled_appointments.html',
                        providers=provider_manager.get_provider_list(),
                        cancelled_appointments=current_slots, # Use list from manager
                        eligible_patients=eligible_patients,
                        current_appointment=appointment,
                        is_temporary_search=False)

@app.route('/assign_appointment/<patient_id>/<appointment_id>', methods=['POST'], strict_slashes=False)
def assign_appointment(patient_id, appointment_id):
    """Assign a patient to a cancelled appointment slot and remove from waitlist"""
    logging.debug(f"Entering assign_appointment for patient_id={patient_id}, appointment_id={appointment_id}")
    # Update wait times
    waitlist_manager.update_wait_times()

    # Get all patients
    all_patients = waitlist_manager.get_all_patients()

    # Find the patient
    patient = None
    for p in all_patients:
        if p.get('id') == patient_id:
            patient = p
            break

    if not patient:
        flash('Patient not found', 'danger')
        logging.debug("Patient not found, redirecting to list_cancelled_appointments")
        return redirect(url_for('list_cancelled_appointments'))

    # Find the appointment using the manager
    appointment = slot_manager.get_slot_by_id(appointment_id)

    if not appointment:
        flash('Appointment not found', 'danger')
        logging.debug("Appointment not found, redirecting to list_cancelled_appointments")
        return redirect(url_for('list_cancelled_appointments'))

    # Check if already matched
    if appointment.get('matched_patient'):
        flash(f'Slot already assigned to {appointment["matched_patient"].get("name", "another patient")}.', 'warning')
        logging.debug("Slot already matched, redirecting to list_cancelled_appointments")
        return redirect(url_for('list_cancelled_appointments'))

    # Check if patient is eligible (using the same helper function)
    match_score = calculate_match_score(patient, appointment) # calculate_match_score uses dicts, compatible
    if match_score == 'none':
        flash(f'{patient.get("name", "Unknown Patient")} is not eligible for this appointment slot.', 'danger')
        logging.debug("Patient not eligible, redirecting to list_cancelled_appointments")
        return redirect(url_for('list_cancelled_appointments'))

    # Attempt to remove patient from waitlist FIRST
    try:
        logging.debug(f"Attempting to remove patient ID: {patient_id}")
        removed = waitlist_manager.remove_patient(patient_id)
        logging.debug(f"Removal result: {removed}")

        if removed:
            # If patient removal was successful, THEN assign patient to appointment using the manager
            assigned = slot_manager.assign_patient_to_slot(appointment_id, patient) # Pass the patient dict

            if assigned:
                flash(f'Successfully assigned {patient.get("name", "Unknown Patient")} to the appointment and removed them from the waitlist.', 'success')
                target_url = url_for('list_cancelled_appointments') # Redirect back to the slots list
                logging.debug(f"Patient removed and assigned successfully, redirecting to: {target_url}")
                return redirect(target_url)
            else:
                # This case means patient was removed but slot assignment failed (e.g., slot disappeared between check and assignment)
                flash('Patient removed from waitlist, but failed to assign to the slot (slot may have been removed). Please check the lists.', 'warning')
                logging.error(f"Removed patient {patient_id} but failed to assign to slot {appointment_id}")
                # Maybe try re-adding the patient? For now, just warn.
                return redirect(url_for('list_cancelled_appointments'))
        else:
            # Patient removal failed
            flash('Failed to remove patient from waitlist. Assignment cancelled.', 'danger')
            logging.debug("Patient removal failed, assignment cancelled, redirecting to list_cancelled_appointments")
            return redirect(url_for('list_cancelled_appointments'))
    except Exception as e:
        logging.error(f"Exception during patient removal or assignment: {e}", exc_info=True)
        flash('An unexpected error occurred while assigning the patient.', 'danger')
        return redirect(url_for('list_cancelled_appointments'))

def calculate_match_score(patient, appointment):
    score = 0
    provider_match = False
    duration_match = False

    # Check provider match
    if patient.get('provider', '').lower() == appointment['provider'].lower():
        provider_match = True
        score += 2
    elif patient.get('provider', '').lower() == 'no preference' or not patient.get('provider'):
        provider_match = True
        score += 1

    # Check duration match
    try:
        patient_duration = int(patient.get('duration', 30))
        appointment_duration = int(appointment['duration'])
    except (ValueError, TypeError):
        patient_duration = 30 # Default if conversion fails
        appointment_duration = 30

    if patient_duration == appointment_duration:
        duration_match = True
        score += 2
    elif patient_duration < appointment_duration:
        duration_match = True
        score += 1

    if provider_match and duration_match and score >= 3:
        return 'perfect'
    elif provider_match or duration_match:
        return 'partial'
    else:
        return 'none'

def find_eligible_patients(cancelled_appointment):
    provider_name = cancelled_appointment['provider']
    eligible_patients = []
    waiting_patients = [p for p in waitlist_manager.get_all_patients() if p.get('status') == 'waiting']
    
    for patient in waiting_patients:
        match_score = calculate_match_score(patient, cancelled_appointment)
        # Only add patients if they are a perfect match
        if match_score == 'perfect':
            patient_copy = patient.copy()
            patient_copy['match_score'] = match_score # Keep score for consistency if needed later
            eligible_patients.append(patient_copy)
            
    # Sort the perfect matches by wait time (longest first)
    def sort_key(patient):
        # Use negative wait time for descending order (longest wait first)
        wait_minutes = -wait_time_to_minutes(patient.get('wait_time', '0 minutes')) 
        return wait_minutes # Return only the wait time for sorting
        
    eligible_patients.sort(key=sort_key)
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

    return redirect(url_for('list_cancelled_appointments'))

@app.route('/edit_cancelled_slot/<appointment_id>', methods=['GET'])
def edit_cancelled_slot(appointment_id):
    """Shows the form to edit a cancelled appointment slot using the manager."""
    # Get the slot using the manager
    appointment_to_edit = slot_manager.get_slot_by_id(appointment_id)

    if not appointment_to_edit:
        flash('Cancelled appointment slot not found.', 'danger')
        return redirect(url_for('list_cancelled_appointments'))

    # Prevent editing if already matched
    if appointment_to_edit.get('matched_patient'):
        flash('Cannot edit a slot that is already matched.', 'warning')
        return redirect(url_for('list_cancelled_appointments'))

    providers = provider_manager.get_provider_list()
    return render_template('edit_cancelled_slot.html',
                           appointment=appointment_to_edit,
                           providers=providers)

@app.route('/update_cancelled_slot/<appointment_id>', methods=['POST'])
def update_cancelled_slot(appointment_id):
    """Updates the details of a cancelled appointment slot using the manager."""
    # Get original slot first to pass back to template on validation failure
    appointment_to_update = slot_manager.get_slot_by_id(appointment_id)

    if not appointment_to_update:
        flash('Cancelled appointment slot not found.', 'danger')
        return redirect(url_for('list_cancelled_appointments'))

    # Check if already matched (manager's update method also checks this)
    if appointment_to_update.get('matched_patient'):
         flash('Cannot edit a slot that is already matched.', 'warning')
         return redirect(url_for('list_cancelled_appointments'))

    # Get updated data from form
    provider = request.form.get('provider')
    duration = request.form.get('duration')
    notes = request.form.get('notes', '')

    # Basic validation
    if not provider or not duration:
        flash('Provider and Duration are required.', 'danger')
        # Redirect back to edit page, passing original appointment data again
        providers = provider_manager.get_provider_list()
        return render_template('edit_cancelled_slot.html',
                               appointment=appointment_to_update, # Use the dict fetched earlier
                               providers=providers)

    # Update using the manager
    updated = slot_manager.update_slot(appointment_id, provider, duration, notes)

    if updated:
        flash('Cancelled appointment slot updated successfully.', 'success')
        logging.debug(f"Updated cancelled slot ID: {appointment_id} via manager")
    else:
        # Manager handles logging, maybe flash a generic error or rely on previous checks
        flash('Failed to update cancelled appointment slot. It might have been removed or matched.', 'danger')

    return redirect(url_for('list_cancelled_appointments'))

if __name__ == '__main__':
    # Ensure provider.csv exists (even if empty)
    if not os.path.exists('provider.csv'):
        with open('provider.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'is_active'])
    
    # Load initial data before starting the server - Handled by manager init
    # try:
        # existing_patients = waitlist_manager.get_all_patients()
        # if not existing_patients:
            # print("Migrating existing waitlist to PatientWaitlistManager...")
            # waitlist_manager.import_from_list(waitlist_manager.get_all_patients()) # This line also had an issue, using get_all_patients as input
    # except Exception as e:
        # print(f"Error during startup: {str(e)}")
    
    # --- Add this line to print the URL map ---
    print("--- Registered URL Routes ---")
    print(app.url_map)
    print("--- End Registered URL Routes ---")
    # --- End added line ---
    
    print("Starting Flask application...")
    app.run(debug=True, host="0.0.0.0", port=7776)
