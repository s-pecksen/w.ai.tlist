from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
    make_response,
)
from datetime import datetime, date, timedelta
import os
from dotenv import load_dotenv
import csv
from io import StringIO
from src.database import get_supabase_client, validate_env_vars
import logging
import json
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from cryptography.fernet import Fernet
import io
import hashlib
from pathlib import Path
import re
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

# Helper functions for wait time conversion
def wait_time_to_days(wait_time_str):
    """Convert wait time string to number of days."""
    if not wait_time_str:
        return 0
    match = re.match(r'(\d+)\s*days?', wait_time_str.lower())
    if match:
        return int(match.group(1))
    return 0

def wait_time_to_minutes(wait_time_str):
    """Convert wait time string to number of minutes."""
    if not wait_time_str:
        return 0
    match = re.match(r'(\d+)\s*minutes?', wait_time_str.lower())
    if match:
        return int(match.group(1))
    return 0

# Load environment variables from .env file
load_dotenv()

# Validate environment variables
validate_env_vars()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Set up data directories
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
USERS_DIR = os.path.join(DATA_DIR, 'users')
SESSIONS_DIR = os.path.join(DATA_DIR, 'flask_sessions')
DIFF_STORE_DIR = os.path.join(DATA_DIR, 'diff_store')

# Create directories if they don't exist
for directory in [DATA_DIR, USERS_DIR, SESSIONS_DIR, DIFF_STORE_DIR]:
    os.makedirs(directory, exist_ok=True)

logger.info(f"Setting up persistent storage at: {DATA_DIR}")

# Configure Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SESSION_SECRET_KEY', 'dev')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_SECURE'] = False  # Set to False for development
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# --- Encryption Setup ---
ENCRYPTION_KEY = os.environ.get("FLASK_APP_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("CRITICAL: FLASK_APP_ENCRYPTION_KEY environment variable not set!")
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "error"

# Get Supabase client
supabase = get_supabase_client()

# Add debug logging for storage setup
logger.info(f"Setting up persistent storage at: {DATA_DIR}")
logger.info(f"Current working directory: {os.getcwd()}")

# Check if /data exists and is writable
if not os.path.exists(DATA_DIR):
    logger.info(f"Creating persistent storage directory at: {DATA_DIR}")
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(USERS_DIR, exist_ok=True)
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    os.makedirs(DIFF_STORE_DIR, exist_ok=True)

# Create and verify session directory
test_file = os.path.join(SESSIONS_DIR, "test_write.tmp")
with open(test_file, "w") as f:
    f.write("test")
os.remove(test_file)
logger.info(f"Session directory verified at: {SESSIONS_DIR}")

# Add these session configurations AFTER path definition
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)  # Sessions last 7 days
app.config["SESSION_FILE_DIR"] = SESSIONS_DIR
app.config["SESSION_FILE_THRESHOLD"] = 500  # Maximum number of sessions
app.config["SESSION_FILE_MODE"] = 0o600  # Secure file permissions
app.config["SESSION_USE_SIGNER"] = True  # Sign the session cookie
app.config["SESSION_COOKIE_SECURE"] = False  # Set to False for development
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERSISTENT_STORAGE_PATH"] = DATA_DIR
app.config["USERS_DIR"] = USERS_DIR

# --- User Class ---
class User(UserMixin):
    def __init__(
        self,
        user_id,
        username,
        clinic_name=None,
        user_name_for_message=None,
        appointment_types=None,
        appointment_types_data=None,
    ):
        self.id = user_id
        self.username = username
        self.clinic_name = clinic_name or ""
        self.user_name_for_message = user_name_for_message or ""
        self.appointment_types = appointment_types or []
        self.appointment_types_data = appointment_types_data or []

    def to_dict(self):
        """Convert user object to dictionary for storage."""
        return {
            "id": self.id,
            "username": self.username,
            "clinic_name": self.clinic_name,
            "user_name_for_message": self.user_name_for_message,
            "appointment_types": self.appointment_types,
            "appointment_types_data": self.appointment_types_data
        }

    @classmethod
    def from_dict(cls, data):
        """Create user object from dictionary."""
        # Parse JSON strings back to lists if needed
        appointment_types = data.get("appointment_types", [])
        appointment_types_data = data.get("appointment_types_data", [])
        
        if isinstance(appointment_types, str):
            appointment_types = json.loads(appointment_types)
        
        if isinstance(appointment_types_data, str):
            appointment_types_data = json.loads(appointment_types_data)
        
        return cls(
            user_id=data.get("id"),
            username=data.get("username"),
            clinic_name=data.get("clinic_name"),
            user_name_for_message=data.get("user_name_for_message"),
            appointment_types=appointment_types,
            appointment_types_data=appointment_types_data
        )

# Flask-Login user loader callback
@login_manager.user_loader
def load_user(user_id):
    """Load user by ID from Supabase, ensuring profile exists."""
    try:
        # The .single() method throws an error if no rows are found, which is what we're seeing.
        # We will handle this case gracefully.
        response = supabase.table("users").select("*").eq("id", user_id).single().execute()
        user_data = response.data
        if user_data:
            return User.from_dict(user_data)
    except Exception as e:
        # This will catch the 'PGRST116' error when no user is found.
        logger.warning(f"Could not load user {user_id}. Profile may be missing. Error: {e}")
    
    # If no user profile is found in our public.users table, it's an inconsistent state.
    # Returning None is the safest option, as it will invalidate the session and prompt a re-login.
    return None

# Add Registration Route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        clinic_name = request.form.get("clinic_name", "").strip()
        user_name_for_message = request.form.get("user_name_for_message", "").strip()

        # Get JSON data from hidden fields
        appointment_types_json = request.form.get("appointment_types_json", "[]")
        providers_json = request.form.get("providers_json", "[]")
        
        logger.info(f"Registration attempt for email: {email}")

        # --- Input Validation ---
        if not email or not password:
            flash("Email and password are required", "error")
            return render_template("register.html")
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            flash("Please enter a valid email address", "error")
            return render_template("register.html")

        # --- Parse JSON data ---
        try:
            appointment_types_data = json.loads(appointment_types_json)
            providers_data = json.loads(providers_json)
            # Extract just the names for the simple list in the 'users' table
            appointment_types_list = [item.get('appointment_type', '') for item in appointment_types_data if item.get('appointment_type')]
        except json.JSONDecodeError:
            flash("There was an error processing the form data.", "error")
            return render_template("register.html")

        # --- Create User in Supabase Auth ---
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "username": email,
                    "clinic_name": clinic_name,
                    "user_name_for_message": user_name_for_message
                }
            }
        })

        if not auth_response.user:
            logger.error(f"Supabase Auth Error: {auth_response.api_error.message if auth_response.api_error else 'No user returned'}")
            flash("Error creating user. An account with this email may already exist.", "error")
            return render_template("register.html")

        user_id = auth_response.user.id
        logger.info(f"Successfully created user in Supabase Auth with ID: {user_id}")
        
        # --- Create User Profile and Initial Data ---
        try:
            # 1. Create the user profile in the 'users' table
            profile_response = supabase.table("users").insert({
                "id": user_id,
                "username": email,
            "clinic_name": clinic_name,
            "user_name_for_message": user_name_for_message,
                "appointment_types": appointment_types_list,
                "appointment_types_data": appointment_types_data
        }).execute()

            if not profile_response.data:
                 raise Exception("Failed to create user profile in database.")

            # 2. Insert initial providers from the registration form
            if providers_data:
                providers_to_insert = [
                    {
                        "user_id": user_id,
                        "first_name": provider.get("first_name"),
                        "last_initial": provider.get("last_initial", "")
                    }
                    for provider in providers_data if provider.get("first_name")
                ]
                if providers_to_insert:
                    supabase.table("providers").insert(providers_to_insert).execute()
                    logger.info(f"Inserted {len(providers_to_insert)} initial providers for user {user_id}")

        except Exception as e:
            # This is a critical failure. We should roll back the user creation.
            logger.error(f"Failed to set up initial data for user {user_id}. Rolling back. Error: {e}", exc_info=True)
            # Use the admin client to delete the user from auth
            supabase.auth.admin.delete_user(user_id)
            
            error_message = "Failed to create user profile."
            if "does not exist" in str(e):
                error_message = "Database is not set up correctly. Please contact support."
            
            flash(error_message, "danger")
            return render_template("register.html")

        # --- Login User and Redirect ---
        user = User(
            user_id=user_id,
            username=email,
            clinic_name=clinic_name,
            user_name_for_message=user_name_for_message
        )
        login_user(user)
        logger.info(f"User {email} registered and logged in successfully")
        flash("Registration successful!", "success")
        return redirect(url_for("index"))

    return render_template("register.html")


# Add Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        remember = request.form.get("remember", False)

        if not email or not password:
            flash("Email and password are required", "error")
            return render_template("login.html")

        # Authenticate with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if not auth_response.user:
            flash("Invalid email or password", "error")
            return render_template("login.html")

        # --- Self-Healing: Check for and create user profile if missing ---
        user_id = auth_response.user.id
        profile_response = supabase.table("users").select("*").eq("id", user_id).execute()

        user_data = None
        if profile_response.data:
            user_data = profile_response.data[0]
        else:
            # Profile is missing, create it now.
            logger.warning(f"User '{email}' logged in but has no profile. Creating one now.")
            
            # Create a default profile. The user can update details later.
            creation_response = supabase.table("users").insert({
                "id": user_id,
                "username": email,
                "clinic_name": f"{email.split('@')[0]}'s Clinic", # A sensible default
            }).execute()

            if not creation_response.data:
                logger.error(f"CRITICAL: Failed to create profile for user {user_id} after login. Check RLS policies.")
                flash("Could not create your user profile after login. Please contact support.", "danger")
                return redirect(url_for('login'))
            
            user_data = creation_response.data[0]
            flash("Welcome! We've set up your new profile.", "success")

        # --- Proceed with login ---
        user = User.from_dict(user_data)
        login_user(user, remember=remember)
        session.permanent = remember
        
        logger.info(f"User {email} logged in successfully")
        flash("Login successful!", "success")
        return redirect(url_for("index"))

    return render_template("login.html")


# Add Logout Route
@app.route("/logout")
@login_required  # User must be logged in to log out
def logout():
    # Sign out from Supabase
    supabase.auth.sign_out()
    # Log out from Flask-Login
    logout_user()
    # Clear session
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for("login"))


@app.route("/slots", methods=["GET"])
@login_required
def slots():
    try:
        # Fetch providers for the user (critical for the form)
        providers_response = supabase.table("providers").select("*").eq("user_id", current_user.id).execute()
        providers = providers_response.data or []
        provider_map = {str(p['id']): f"{p['first_name']} {p['last_initial'] or ''}".strip() for p in providers}
    except Exception as e:
        logger.error(f"Failed to load provider data for user {current_user.id}: {e}", exc_info=True)
        flash("Could not load provider data, which is required for the slots page.", "danger")
        return redirect(url_for('index'))

    all_slots = []
    try:
        # Fetch all slots for the user (non-critical, may not exist yet)
        slots_response = supabase.table("cancelled_slots").select("*").eq("user_id", current_user.id).execute()
        all_slots = slots_response.data or []
        for slot in all_slots:
            # The 'provider' column stores the provider's UUID. We'll replace it with the name for display.
            provider_name = provider_map.get(str(slot.get("provider")))
            if provider_name:
                slot["provider_name"] = provider_name # Keep original ID if needed elsewhere
            else:
                slot["provider_name"] = "Unknown Provider" # Fallback
    except Exception as e:
        logger.warning(f"Could not load slots for user {current_user.id}. The table may not exist yet. Error: {e}")
        # If this fails, all_slots will remain an empty list, and the page will still render.
    
    appointment_types_data = current_user.appointment_types_data or []
    duration_map = {
        item["appointment_type"].lower().replace(" ", "_"): item["durations"]
        for item in appointment_types_data
        if "appointment_type" in item and "durations" in item
    }

    current_appointment_id_in_session = session.get("current_appointment_id")
    current_appointment_for_matching = None
    eligible_patients_data = []

    if current_appointment_id_in_session:
        slot_for_match = next((s for s in all_slots if s.get('id') == current_appointment_id_in_session), None)
        if slot_for_match and slot_for_match.get('status') == 'available': # Only find matches for available slots
            current_appointment_for_matching = slot_for_match
            logging.info(f"Finding matches for slot {current_appointment_id_in_session}: {slot_for_match}")
            
            # Logic to find eligible patients for this slot
            try:
                waitlist_response = supabase.table("patients").select("*").eq("user_id", current_user.id).execute()
                all_patients = waitlist_response.data or []
            except Exception as e:
                logger.error(f"Failed to load patients data for match finding: {e}", exc_info=True)
                flash("Could not load patients to find matches.", "danger")
                all_patients = []

            slot_duration = int(slot_for_match.get("duration", 0))
            slot_provider_id = slot_for_match.get("provider") # This is the UUID
            
            slot_date_str = slot_for_match.get("date")
            slot_period = slot_for_match.get("slot_period", "").upper()
            slot_dt = None
            if isinstance(slot_date_str, str):
                slot_dt = datetime.strptime(slot_date_str, "%Y-%m-%d")
            elif isinstance(slot_date_str, datetime):
                slot_dt = slot_date_str

            logging.info(f"Slot requirements - Duration: {slot_duration}, Provider: {slot_provider_id}, Date: {slot_dt}, Period: {slot_period}")

            for patient in all_patients:
                if patient.get("status") != "waiting":
                    logging.info(f"Patient {patient.get('id')} skipped: Status is {patient.get('status')} (not waiting)")
                    continue

                patient_duration = int(patient.get("duration", 0))
                if patient_duration > slot_duration:
                    logging.info(f"Patient {patient.get('id')} skipped: Duration mismatch (patient: {patient_duration} > slot: {slot_duration})")
                    continue

                # The patient provider preference is a name, but the slot has an ID.
                # We need to get the provider name from our map to compare.
                slot_provider_name = provider_map.get(str(slot_provider_id), "").lower()
                patient_provider_pref = patient.get("provider", "no preference").lower()
                if patient_provider_pref != "no preference" and patient_provider_pref != slot_provider_name:
                    logging.info(f"Patient {patient.get('id')} skipped: Provider mismatch (patient: '{patient_provider_pref}' != slot: '{slot_provider_name}')")
                    continue
                
                # Availability Check
                if slot_dt: # Only proceed if slot_dt is valid
                    patient_availability = patient.get("availability", {})
                    patient_availability_mode = patient.get("availability_mode", "available")
                    slot_weekday = slot_dt.strftime("%A") # Full day name e.g. Monday
                    
                    is_patient_available_for_slot_period = False
                    if patient_availability:
                        day_periods = patient_availability.get(slot_weekday, [])
                        if slot_period in day_periods:
                            is_patient_available_for_slot_period = True
                    
                    if patient_availability_mode == "available":
                        if not day_periods or not is_patient_available_for_slot_period: # Must be explicitly available
                            logging.info(f"Patient {patient.get('id')} skipped: Availability mismatch (mode: available, day: {slot_weekday}, period: {slot_period}, prefs: {day_periods})")
                            continue
                    elif patient_availability_mode == "unavailable":
                        if patient_availability and is_patient_available_for_slot_period: # Must NOT be explicitly unavailable
                            logging.info(f"Patient {patient.get('id')} skipped: Availability mismatch (mode: unavailable, day: {slot_weekday}, period: {slot_period}, prefs: {day_periods})")
                            continue
                else: # If slot_dt is not valid, cannot perform date-based availability check
                    logging.debug(f"Skipping date-based availability for patient {patient.get('id')} due to invalid slot date for slot {slot_for_match.get('id')}")

                logging.info(f"Patient {patient.get('id')} matched for slot {current_appointment_id_in_session}")
                eligible_patients_data.append(patient)
            
            # Sort eligible patients (e.g., by urgency, then wait time)
            def sort_key_eligible(p):
                urgency_order = {'high': 0, 'medium': 1, 'low': 2}
                wait_days_val = wait_time_to_days(p.get('wait_time', '0 days'))
                return (urgency_order.get(p.get('urgency', 'medium'), 99), -wait_days_val)
            eligible_patients_data.sort(key=sort_key_eligible)

            logging.info(f"Found {len(eligible_patients_data)} eligible patients for slot {current_appointment_id_in_session}")

    return render_template("slots.html",
                           cancelled_appointments=all_slots,
                           providers=providers,
                           has_providers=len(providers) > 0,
                           appointment_types=current_user.appointment_types or [],
                           appointment_types_data=appointment_types_data,
                           duration_map=duration_map,
                           current_user_name=current_user.user_name_for_message or "the scheduling team",
                           current_clinic_name=current_user.clinic_name or "our clinic",
                           current_appointment_id_for_matching=current_appointment_id_in_session,
                           current_appointment=current_appointment_for_matching,
                           eligible_patients=eligible_patients_data
                           )


# Modify Index Route (Example of protecting and using current_user)
@app.route("/", methods=["GET"])
@login_required
def index():
    try:
        # Core data: providers and user info are essential.
        providers_response = supabase.table("providers").select("*").eq("user_id", current_user.id).execute()
        providers = providers_response.data or []
        appointment_types = current_user.appointment_types or []
        appointment_types_data = current_user.appointment_types_data or []

        # Optional data: These may be empty or unavailable for a new user.
        waitlist = []
        try:
            waitlist_response = supabase.table("patients").select("*").eq("user_id", current_user.id).execute()
            waitlist = waitlist_response.data or []
        except Exception as e:
            logger.warning(f"Could not load patients for user {current_user.id}. It may not exist yet. Error: {e}")

        all_slots = []
        try:
            slots_response = supabase.table("cancelled_slots").select("*").eq("user_id", current_user.id).execute()
            all_slots = slots_response.data or []
        except Exception as e:
            logger.warning(f"Could not load slots for user {current_user.id}. It may not exist yet. Error: {e}")

        # Proceed with processing, which is now safe for empty lists.
        slot_map = {s['id']: s for s in all_slots}

        for patient in waitlist:
             if patient.get("status") == "pending" and patient.get("proposed_slot_id"):
                 proposed_slot = slot_map.get(patient["proposed_slot_id"])
                 if proposed_slot:
                     slot_date_display = proposed_slot.get("date", "")
                     if isinstance(slot_date_display, str) and slot_date_display:
                         try:
                             slot_date_display = datetime.strptime(slot_date_display, '%Y-%m-%d').strftime('%a, %b %d')
                         except (ValueError, TypeError):
                             pass
                     elif isinstance(slot_date_display, (datetime, date)):
                         slot_date_display = slot_date_display.strftime('%a, %b %d')
                     patient["proposed_slot_details"] = f"Slot on {slot_date_display} ({proposed_slot.get('slot_period', '')}) w/ {proposed_slot.get('provider')}"

        duration_map = {
            item["appointment_type"].lower().replace(" ", "_"): item["durations"]
            for item in appointment_types_data if "appointment_type" in item and "durations" in item
        }

        def sort_key_waitlist(p):
            status_order = {'pending': 0, 'waiting': 1}
            wait_minutes = wait_time_to_minutes(p.get('wait_time', '0 minutes'))
            return (status_order.get(p.get('status', 'waiting'), 99), -wait_minutes)
        sorted_waitlist = sorted(waitlist, key=sort_key_waitlist)

        if not providers:
            flash("Get started by adding your providers in the settings page.", "info")

        return render_template(
            "index.html",
            providers=providers,
            waitlist=sorted_waitlist,
            has_providers=len(providers) > 0,
            appointment_types=appointment_types,
            appointment_types_data=appointment_types_data,
            duration_map=duration_map,
            current_clinic_name=current_user.clinic_name or "our clinic",
            current_user_name=current_user.user_name_for_message or "the scheduling team"
        )
    except Exception as e:
        # This is a fallback for unexpected errors.
        logging.error(f"A critical error occurred in the index route: {e}", exc_info=True)
        flash("A critical error occurred. Please try logging in again.", "danger")
        return redirect(url_for('login'))


@app.route("/add_patient", methods=["POST"])
@login_required
def add_patient():
    # Get user-specific managers
    waitlist_response = supabase.table("patients").select("*").eq("user_id", current_user.id).execute()
    waitlist = waitlist_response.data

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

    # --- Add Patient via Manager ---
    waitlist_response = supabase.table("patients").insert({
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
    }).execute()

    flash("Patient added successfully.", "success")

    # This return is outside the try/except block
    return redirect(url_for("index") + "#add-patient-form")


@app.route("/remove_patient/<patient_id>", methods=["POST"])
@login_required
def remove_patient(patient_id):
    """Remove a patient from the patients list"""
    waitlist_response = supabase.table("patients").delete().eq("id", patient_id).eq("user_id", current_user.id).execute()
    success = waitlist_response.rowcount > 0
    if success:
        flash("Patient removed successfully", "success")
    else:
        flash("Error removing patient", "danger")
    return redirect(url_for("index") + "#waitlist-table")


@app.route("/update_patient/<patient_id>", methods=["POST"])
@login_required
def update_patient(patient_id):
    """Update a patient's information"""
    waitlist_response = supabase.table("patients").select("*").eq("id", patient_id).eq("user_id", current_user.id).execute()
    patient = waitlist_response.data[0] if waitlist_response.data else None
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
    success = waitlist_response = supabase.table("patients").update({
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
    }).eq("id", patient_id).eq("user_id", current_user.id).execute()
    if success:
        flash("Patient updated successfully", "success")
    else:
        flash("Error updating patient", "danger")
    return redirect(url_for("index"))


@app.route("/add_cancelled_appointment", methods=["POST"])
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
        return redirect(url_for("slots"))

    # Determine AM/PM from time for efficient filtering
    try:
        time_obj = datetime.strptime(slot_time_str, "%H:%M").time()
        slot_period = "PM" if time_obj.hour >= 12 else "AM"
    except ValueError:
        flash("Invalid time format. Please use HH:MM.", "danger")
        return redirect(url_for("slots"))
    
    try:
        # Include user_id with the insert for RLS
        insert_response = supabase.table("cancelled_slots").insert({
            "provider": provider,
            "date": slot_date,
            "time": slot_time_str,
            "duration": duration,
            "notes": notes,
            "slot_period": slot_period,
            "user_id": current_user.id
        }).execute()
        
        if insert_response.data:
            flash("Open slot added successfully", "success")
        else:
            flash("Error adding open slot.", "danger")
            
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")

    return redirect(url_for("slots"))


@app.route("/remove_cancelled_slot/<appointment_id>", methods=["POST"])
@login_required
def remove_cancelled_slot(appointment_id):
    """Remove a cancelled appointment (open slot)"""
    try:
        delete_response = supabase.table("cancelled_slots").delete().eq("id", appointment_id).eq("user_id", current_user.id).execute()
        if delete_response.data:
            flash("Open slot removed successfully", "success")
        else:
            flash("Error removing open slot. It may have already been removed.", "danger")
    except Exception as e:
        logger.error(f"Error removing slot {appointment_id}: {e}", exc_info=True)
        flash("An error occurred while removing the slot.", "danger")
    return redirect(url_for("slots"))


@app.route("/update_cancelled_slot/<appointment_id>", methods=["POST"])
@login_required
def update_cancelled_slot(appointment_id):
    """Update a cancelled appointment (open slot)"""
    logging.info(f"Updating slot {appointment_id} with form data: {request.form}")
    
    provider_id = request.form.get("provider")
    slot_date = request.form.get("date")
    slot_time_str = request.form.get("time")
    duration = request.form.get("duration")
    notes = request.form.get("notes", "")
    
    if not all([provider_id, slot_date, slot_time_str, duration]):
        missing_fields = [f for f, v in [("provider", provider_id), ("date", slot_date), 
                                       ("time", slot_time_str), ("duration", duration)] if not v]
        logging.error(f"Missing required fields: {missing_fields}")
        flash("All required fields must be filled", "danger")
        return redirect(url_for("slots"))
        
    try:
        time_obj = datetime.strptime(slot_time_str, "%H:%M").time()
        slot_period = "PM" if time_obj.hour >= 12 else "AM"
        slot_time_str_formatted = time_obj.strftime("%H:%M") # Ensure consistent format
    
        update_data = {
            "provider": provider_id,
            "date": slot_date,
            "time": slot_time_str_formatted,
            "duration": duration,
            "notes": notes,
            "slot_period": slot_period
        }
    
        update_response = supabase.table("cancelled_slots").update(update_data).eq("id", appointment_id).eq("user_id", current_user.id).execute()
    
        if update_response.data:
            logging.info(f"Successfully updated slot {appointment_id}")
            flash("Open slot updated successfully", "success")
        else:
            logging.error(f"Failed to update slot {appointment_id}")
            flash("Error updating open slot. It may no longer exist.", "danger")

    except ValueError:
        flash("Invalid time format. Please use HH:MM.", "danger")
    except Exception as e:
        logger.error(f"Exception updating slot {appointment_id}: {e}", exc_info=True)
        flash(f"An error occurred: {e}", "danger")
        
    return redirect(url_for("slots"))


@app.route("/find_matches_for_appointment/<appointment_id>", methods=["POST"])
@login_required
def find_matches_for_appointment(appointment_id):
    """Find matching patients for a cancelled appointment"""
    session["current_appointment_id"] = appointment_id
    return redirect(url_for("slots") + "#eligible-patients-section")


@app.route("/propose_slot/<slot_id>/<patient_id>", methods=["POST"])
@login_required
def propose_slot(slot_id, patient_id):
    """Marks a slot and patient as pending confirmation."""
    try:
        patient_resp = supabase.table("patients").select("name").eq("id", patient_id).eq("user_id", current_user.id).single().execute()
        patient_name = patient_resp.data.get("name", "Unknown") if patient_resp.data else "Unknown"

        slot_update_resp = supabase.table("cancelled_slots").update({
            "status": "pending", 
            "proposed_patient_id": patient_id, 
            "proposed_patient_name": patient_name
        }).eq("id", slot_id).eq("user_id", current_user.id).execute()

        patient_update_resp = supabase.table("patients").update({
            "status": "pending", 
            "proposed_slot_id": slot_id
        }).eq("id", patient_id).eq("user_id", current_user.id).execute()

        if slot_update_resp.data and patient_update_resp.data:
            flash("Slot proposed and marked as pending confirmation.", "info")
            session.pop("current_appointment_id", None)
        else:
            raise Exception("Failed to update slot or patient status.")

    except Exception as e:
        logger.error(f"Error proposing slot: {e}", exc_info=True)
        flash("Error proposing slot. The slot may have been taken or the patient is no longer available.", "danger")
        # Attempt to roll back state if something went wrong
        supabase.table("cancelled_slots").update({"status": "available", "proposed_patient_id": None, "proposed_patient_name": None}).eq("id", slot_id).execute()
        supabase.table("patients").update({"status": "waiting", "proposed_slot_id": None}).eq("id", patient_id).execute()

    return redirect(request.referrer or url_for('index'))


@app.route("/confirm_booking/<slot_id>/<patient_id>", methods=["POST"])
@login_required
def confirm_booking(slot_id, patient_id):
    """Confirms the booking, removing the patient and the slot."""
    try:
        # For safety, ensure the slot and patient are in the correct pending state before deleting.
        slot_resp = supabase.table("cancelled_slots").select("id").eq("id", slot_id).eq("proposed_patient_id", patient_id).eq("user_id", current_user.id).single().execute()
        patient_resp = supabase.table("patients").select("id").eq("id", patient_id).eq("proposed_slot_id", slot_id).eq("user_id", current_user.id).single().execute()

        if not slot_resp.data or not patient_resp.data:
            raise Exception("Mismatch in pending slot/patient data.")

        # If checks pass, delete both records.
        supabase.table("patients").delete().eq("id", patient_id).execute()
        supabase.table("cancelled_slots").delete().eq("id", slot_id).execute()
        
        flash("Booking confirmed. Patient removed from patients list and slot closed.", "success")
    except Exception as e:
        logger.error(f"Error confirming booking: {e}", exc_info=True)
        flash("Error confirming booking. The slot or patient may have been modified.", "danger")

    return redirect(url_for("index"))


@app.route("/cancel_proposal/<slot_id>/<patient_id>", methods=["POST"])
@login_required
def cancel_proposal(slot_id, patient_id):
    """Cancels a pending proposal, making the slot and patient available again."""
    try:
        slot_reset_resp = supabase.table("cancelled_slots").update({
            "status": "available", 
            "proposed_patient_id": None, 
            "proposed_patient_name": None
        }).eq("id", slot_id).eq("user_id", current_user.id).execute()

        patient_reset_resp = supabase.table("patients").update({
            "status": "waiting", 
            "proposed_slot_id": None
        }).eq("id", patient_id).eq("user_id", current_user.id).execute()

        if slot_reset_resp.data and patient_reset_resp.data:
            flash("Proposal cancelled. Slot and patient are available again.", "info")
        else:
            raise Exception("Failed to reset slot or patient.")
            
    except Exception as e:
        logger.error(f"Error cancelling proposal: {e}", exc_info=True)
        flash("Error cancelling proposal. Please check the data and try again.", "danger")

    return redirect(request.referrer or url_for('index'))


@app.route("/upload_csv", methods=["GET", "POST"])
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
                existing_patients_resp = supabase.table("patients").select("name, phone").eq("user_id", current_user.id).execute()
                existing_patients = set((p['name'].lower(), p['phone']) for p in (existing_patients_resp.data or []))
                
                providers_resp = supabase.table("providers").select("first_name, last_initial").eq("user_id", current_user.id).execute()
                valid_providers = {f"{p['first_name']} {p['last_initial'] or ''}".strip().lower() for p in (providers_resp.data or [])}
                valid_providers.add("no preference")

                valid_appointment_types = {apt['appointment_type'].lower().replace(' ', '_') for apt in (current_user.appointment_types_data or [])}

                # Validation helpers
                def validate_provider(val):
                    return val if (val or "no preference").lower() in valid_providers else "no preference"

                for row in csv_input:
                    norm_row = {k.lower().strip().replace(" ", "_"): v for k, v in row.items()}
                    name, phone = norm_row.get("name", "").strip(), norm_row.get("phone", "").strip()

                    if not name or not phone or (name.lower(), phone) in existing_patients:
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
                        # Include other fields from CSV as needed
                    }
                    patients_to_add.append(patient_data)
                    existing_patients.add((name.lower(), phone))

                if patients_to_add:
                    insert_response = supabase.table("patients").insert(patients_to_add).execute()
                    added_count = len(insert_response.data)
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


@app.route("/api/find_matches_for_patient/<patient_id>")
@login_required
def api_find_matches_for_patient(patient_id):
    try:
        # Fetch patient data
        patient_resp = supabase.table("patients").select("*").eq("id", patient_id).eq("user_id", current_user.id).single().execute()
        patient = patient_resp.data
        if not patient:
            return jsonify({"error": "Patient not found"}), 404
        logging.info(f"Finding matches for patient {patient_id}: {patient}")

        # Fetch providers to map IDs to names
        providers_response = supabase.table("providers").select("id, first_name, last_initial").eq("user_id", current_user.id).execute()
        provider_map = {str(p['id']): f"{p['first_name']} {p['last_initial'] or ''}".strip() for p in (providers_response.data or [])}

        if patient.get("status", "waiting") != "waiting":
            return jsonify({"error": "Patient is not currently waiting", "status": patient.get("status")}), 400

        # Get all available slots
        slots_resp = supabase.table("cancelled_slots").select("*").eq("user_id", current_user.id).eq("status", "available").execute()
        available_slots = slots_resp.data or []
        logging.info(f"Found {len(available_slots)} available slots for patient {patient_id}")

        # Filter slots based on patient requirements
        matching_slots = []
        patient_duration = int(patient.get("duration", 0))
        patient_provider_pref = patient.get("provider", "no preference").lower()
        patient_availability = patient.get("availability", {})
        patient_availability_mode = patient.get("availability_mode", "available")

        logging.info(f"Patient requirements - Duration: {patient_duration}, Provider: {patient_provider_pref}, Availability Mode: {patient_availability_mode}")

        for slot in available_slots:
            # Check duration
            slot_duration = int(slot.get("duration", 0))
            if patient_duration > slot_duration:
                continue

            # Check provider
            slot_provider_id = str(slot.get("provider"))
            slot_provider_name = provider_map.get(slot_provider_id, "").lower()
            if patient_provider_pref != "no preference" and patient_provider_pref != slot_provider_name:
                continue

            # Check availability
            slot_date_str = slot.get("date")
            slot_period = slot.get("slot_period", "").upper()

            slot_date = None
            if isinstance(slot_date_str, str):
                try:
                    slot_date = datetime.strptime(slot_date_str, "%Y-%m-%d")
                except ValueError: 
                    continue
            elif isinstance(slot_date_str, datetime):
                slot_date = slot_date_str
            else:
                continue

            if patient_availability:
                slot_weekday = slot_date.strftime("%A")
                day_periods = patient_availability.get(slot_weekday, [])
                is_available_on_day_period = slot_period in day_periods

                if patient_availability_mode == "available" and not is_available_on_day_period:
                    continue
                if patient_availability_mode == "unavailable" and is_available_on_day_period:
                    continue

            # If all checks pass, add the slot, enriching it with the provider name for the UI
            slot['provider_name'] = provider_map.get(slot_provider_id, "Unknown")
            matching_slots.append(slot)

        # Sort matching slots by date
        matching_slots.sort(key=lambda s: s.get("date", str(date.max)))

        logging.info(f"Returning {len(matching_slots)} matching slots for patient {patient_id}")
        return jsonify({"patient": patient, "matching_slots": matching_slots})

    except Exception as e:
        logger.error(f"Error in api_find_matches_for_patient: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred."}), 500


@app.route("/providers", methods=["GET"])
@login_required
def list_providers():
    try:
        providers_response = supabase.table("providers").select("*").eq("user_id", current_user.id).order("first_name").execute()
        providers = providers_response.data or []
    except Exception as e:
        flash(f"Error loading providers: {e}", "danger")
        providers = []
    return render_template("providers.html", providers=providers)


@app.route("/add_provider", methods=["POST"])
@login_required
def add_provider():
    first_name = request.form.get("first_name", "").strip()
    last_initial = request.form.get("last_initial", "").strip()

    if not first_name:
        flash("Provider first name is required.", "warning")
        return redirect(url_for("list_providers"))

    try:
        # Add the provider with the user_id for RLS
        insert_response = supabase.table("providers").insert({
            "first_name": first_name,
            "last_initial": last_initial,
            "user_id": current_user.id
        }).execute()
        
        if insert_response.data:
            flash("Provider added successfully.", "success")
        else:
            flash("Could not add provider. They may already exist.", "warning")
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")

    return redirect(url_for("list_providers"))


@app.route("/remove_provider", methods=["POST"])
@login_required
def remove_provider():
    provider_id = request.form.get("provider_id") # Safer to remove by primary key
    if not provider_id:
        flash("Provider ID not provided for removal.", "warning")
        return redirect(url_for("list_providers"))
        
    try:
        # RLS policies will ensure the user can only delete their own providers.
        # The .eq("user_id", current_user.id) is technically redundant if RLS is correct, but good for defense-in-depth.
        delete_response = supabase.table("providers").delete().eq("id", provider_id).eq("user_id", current_user.id).execute()
        
        if delete_response.data:
            flash("Provider removed successfully.", "success")
        else:
            flash("Provider not found or could not be removed.", "danger")
    except Exception as e:
        flash(f"An error occurred: {e}", "danger")
        
    return redirect(url_for("list_providers"))


@app.route("/edit_patient/<patient_id>", methods=["GET"])
@login_required
def edit_patient(patient_id):
    try:
        patient_response = supabase.table("patients").select("*").eq("id", patient_id).eq("user_id", current_user.id).single().execute()
        patient = patient_response.data
        if not patient:
            flash("Patient not found.", "danger")
            return redirect(url_for("index"))
    
        providers_response = supabase.table("providers").select("*").eq("user_id", current_user.id).execute()
        providers = providers_response.data or []
        
        appointment_types = current_user.appointment_types or []
        appointment_types_data = current_user.appointment_types_data or []

        return render_template("edit_patient.html",
                               patient=patient,
                               providers=providers,
                               has_providers=len(providers) > 0,
                               appointment_types=appointment_types,
                               appointment_types_data=appointment_types_data)
    except Exception as e:
        logger.error(f"Error loading edit patient page for {patient_id}: {e}", exc_info=True)
        flash("Could not load patient data for editing.", "danger")
        return redirect(url_for("index"))


@app.route("/debug/session")
def debug_session():
    if not app.debug:
        return "Debug route not available in production", 403
    return jsonify({"error": "This endpoint is deprecated"}), 410

@app.route("/debug/write_test")
def debug_write_test():
    return jsonify({"error": "This endpoint is deprecated"}), 410

@app.route("/debug/list_user_files/<username>")
def debug_list_user_files(username):
    return jsonify({"error": "This endpoint is deprecated"}), 410

@app.route("/debug/show_profile/<username>")
def debug_show_profile(username):
    return jsonify({"error": "This endpoint is deprecated"}), 410

@app.route("/setup/database", methods=["GET", "POST"])
@login_required
def setup_database():
    """Database setup and debugging route"""
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "check_tables":
            tables_status = {}
            required_tables = ["users", "providers", "patients", "cancelled_slots"]
            
            for table in required_tables:
                try:
                    response = supabase.table(table).select("count", count="exact").limit(1).execute()
                    tables_status[table] = {"exists": True, "count": response.count}
                except Exception as e:
                    tables_status[table] = {"exists": False, "error": str(e)}
            
            return jsonify({"tables": tables_status})
        
        elif action == "create_tables":
            # This would require admin privileges in Supabase
            # For now, just return instructions
            return jsonify({
                "message": "Table creation requires admin access to Supabase. Please create tables manually.",
                "instructions": [
                    "1. Go to your Supabase dashboard",
                    "2. Navigate to SQL Editor",
                    "3. Run the following SQL commands:",
                    "",
                    "CREATE TABLE users (",
                    "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),",
                    "  username TEXT UNIQUE NOT NULL,",
                    "  clinic_name TEXT,",
                    "  user_name_for_message TEXT,",
                    "  appointment_types JSONB DEFAULT '[]',",
                    "  appointment_types_data JSONB DEFAULT '[]',",
                    "  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()",
                    ");",
                    "",
                    "CREATE TABLE providers (",
                    "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),",
                    "  user_id UUID REFERENCES users(id) ON DELETE CASCADE,",
                    "  first_name TEXT NOT NULL,",
                    "  last_initial TEXT,",
                    "  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()",
                    ");",
                    "",
                    "CREATE TABLE patients (",
                    "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),",
                    "  user_id UUID REFERENCES users(id) ON DELETE CASCADE,",
                    "  name TEXT NOT NULL,",
                    "  phone TEXT NOT NULL,",
                    "  email TEXT,",
                    "  reason TEXT,",
                    "  urgency TEXT DEFAULT 'medium',",
                    "  appointment_type TEXT,",
                    "  duration INTEGER DEFAULT 30,",
                    "  provider TEXT,",
                    "  availability JSONB DEFAULT '{}',",
                    "  availability_mode TEXT DEFAULT 'available',",
                    "  status TEXT DEFAULT 'waiting',",
                    "  proposed_slot_id UUID,",
                    "  wait_time TEXT DEFAULT '0 minutes',",
                    "  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),",
                    "  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()",
                    ");",
                    "",
                    "CREATE TABLE cancelled_slots (",
                    "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),",
                    "  user_id UUID REFERENCES users(id) ON DELETE CASCADE,",
                    "  provider TEXT NOT NULL,",
                    "  date DATE NOT NULL,",
                    "  time TIME NOT NULL,",
                    "  duration INTEGER NOT NULL,",
                    "  slot_period TEXT,",
                    "  notes TEXT,",
                    "  status TEXT DEFAULT 'available',",
                    "  proposed_patient_id UUID,",
                    "  proposed_patient_name TEXT,",
                    "  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()",
                    ");"
                ]
            })
    
    return render_template("setup_database.html")

# Add before_request handler for security headers
@app.before_request
def add_security_headers():
    """Add security headers to all responses."""
    # Don't return a response here, just set headers on the request
    pass

# Add after_request handler for security headers
@app.after_request
def add_security_headers_after(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; img-src 'self' data:;"
    return response

# Add after_request handler for CORS
@app.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# Add request logging middleware
@app.before_request
def log_request_info():
    """Log request information."""
    logger.info('Headers: %s', request.headers)
    logger.info('Body: %s', request.get_data())

# Add response logging middleware
@app.after_request
def log_response_info(response):
    """Log response information."""
    logger.info('Response Status: %s', response.status)
    logger.info('Response Headers: %s', response.headers)
    return response

if __name__ == "__main__":
    # Create session directory if it doesn't exist
    session_dir = os.path.join(DATA_DIR, "flask_sessions")
    os.makedirs(session_dir, exist_ok=True)
    logger.info(f"Created session directory at: {session_dir}")
    
    logger.info("Session configuration:")
    logger.info("SECRET_KEY is set: %s", bool(app.secret_key))
    logger.info("SESSION_TYPE: %s", app.config.get("SESSION_TYPE"))
    logger.info("SESSION_FILE_DIR: %s", app.config.get("SESSION_FILE_DIR"))
    logger.info("SESSION_PERMANENT: %s", app.config.get("SESSION_PERMANENT"))
    
    app.run(host='0.0.0.0', port=7860, debug=True)  # Enable debug mode temporarily
