from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from datetime import datetime, date, timedelta
import os
from dotenv import load_dotenv
import csv
from io import StringIO
from src.database import init_db, DatabaseManager, supabase
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
from src.diffstore import save_to_diff_store, load_from_diff_store
from src.encryption_utils import load_decrypted_json, save_encrypted_json
from flask_session import Session
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
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = SESSIONS_DIR
app.config['SESSION_FILE_THRESHOLD'] = 500
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Initialize session
Session(app)

# --- Encryption Setup ---
ENCRYPTION_KEY = os.environ.get("FLASK_APP_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("CRITICAL: FLASK_APP_ENCRYPTION_KEY environment variable not set!")
try:
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
except Exception as e:
    raise ValueError(f"CRITICAL: Invalid FLASK_APP_ENCRYPTION_KEY. It must be a 32 url-safe base64-encoded bytes. Error: {e}")

# --- Flask App Initialization ---
app.secret_key = os.environ.get("FLASK_SESSION_SECRET_KEY", os.urandom(24))

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "error"

# Add debug logging for storage setup
logger.info(f"Setting up persistent storage at: {DATA_DIR}")
logger.info(f"Current working directory: {os.getcwd()}")

# Check if /data exists and is writable
if not os.path.exists(DATA_DIR):
    logger.info(f"Creating persistent storage directory at: {DATA_DIR}")
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(USERS_DIR, exist_ok=True)
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        os.makedirs(DIFF_STORE_DIR, exist_ok=True)
    except Exception as e:
        logger.error(f"Error creating persistent storage directories: {e}")
        raise RuntimeError(f"Failed to create persistent storage directories: {e}")

# Create and verify session directory
try:
    # Test write permissions
    test_file = os.path.join(SESSIONS_DIR, "test_write.tmp")
    with open(test_file, "w") as f:
        f.write("test")
    os.remove(test_file)
    logger.info(f"Session directory verified at: {SESSIONS_DIR}")
except Exception as e:
    logger.error(f"Error setting up session directory: {e}")
    raise RuntimeError(f"Failed to set up session directory: {e}")

# Add these session configurations AFTER path definition
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)  # Sessions last 7 days
app.config["SESSION_FILE_DIR"] = SESSIONS_DIR
app.config["SESSION_FILE_THRESHOLD"] = 500  # Maximum number of sessions
app.config["SESSION_FILE_MODE"] = 0o600  # Secure file permissions
app.config["SESSION_USE_SIGNER"] = True  # Sign the session cookie
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERSISTENT_STORAGE_PATH"] = DATA_DIR
app.config["USERS_DIR"] = USERS_DIR

# Initialize the database
init_db(app)

# Password validation
def validate_password(password):
    """Validate password strength."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"

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
            try:
                appointment_types = json.loads(appointment_types)
            except json.JSONDecodeError:
                appointment_types = []
                
        if isinstance(appointment_types_data, str):
            try:
                appointment_types_data = json.loads(appointment_types_data)
            except json.JSONDecodeError:
                appointment_types_data = []
        
        return cls(
            user_id=data.get("id"),
            username=data.get("username"),
            clinic_name=data.get("clinic_name"),
            user_name_for_message=data.get("user_name_for_message"),
            appointment_types=appointment_types,
            appointment_types_data=appointment_types_data
        )

# --- User Management Functions ---
def save_user(user):
    """Save user to database"""
    try:
        db_manager = DatabaseManager(user.id, app.cipher_suite)
        success = db_manager.update_user(
            user.id,
            username=user.username,
            clinic_name=user.clinic_name,
            user_name_for_message=user.user_name_for_message,
            appointment_types=user.appointment_types,
            appointment_types_data=user.appointment_types_data
        )
        if success:
            logging.info(f"Successfully saved user profile for: {user.username}")
            return True
        else:
            logging.error(f"Failed to save user profile for: {user.username}")
            return False
    except Exception as e:
        logging.error(f"Error saving user profile: {e}", exc_info=True)
        return False

def get_user_by_username(username):
    """Get user by username from database"""
    try:
        db_manager = DatabaseManager("system", app.cipher_suite)
        user_data = db_manager.get_user_by_username(username)
        if not user_data:
            logging.warning(f"No user data found for username: {username}")
            return None
        logging.info(f"Successfully loaded user profile for: {username}")
        return User.from_dict(user_data)
    except Exception as e:
        logging.error(f"Error getting user by username: {e}", exc_info=True)
        return None

def get_user_by_id(user_id):
    """Get user by ID from database"""
    try:
        db_manager = DatabaseManager("system", app.cipher_suite)
        user_data = db_manager.get_user_by_id(user_id)
        if not user_data:
            logging.warning(f"No user data found for ID: {user_id}")
            return None
        return User.from_dict(user_data)
    except Exception as e:
        logging.error(f"Error getting user by ID: {e}", exc_info=True)
        return None

def username_exists(username):
    """Check if username exists in database"""
    try:
        db_manager = DatabaseManager("system", app.cipher_suite)
        return db_manager.username_exists(username)
    except Exception as e:
        logging.error(f"Error checking username existence: {e}", exc_info=True)
        return False

# Flask-Login user loader callback
@login_manager.user_loader
def load_user(user_id):
    """Load user by ID"""
    try:
        db_manager = DatabaseManager("system", app.cipher_suite)
        user_data = db_manager.get_user_by_id(user_id)
        if user_data:
            return User.from_dict(user_data)
    except Exception as e:
        logging.error(f"Error loading user: {e}", exc_info=True)
    return None

# Function to get user-specific managers
def get_user_managers(username):
    """Get managers initialized with user-specific data paths"""
    return (
        DatabaseManager(username, app.cipher_suite),
        DatabaseManager(username, app.cipher_suite),
        DatabaseManager(username, app.cipher_suite)
    )

# Add Registration Route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        clinic_name = request.form.get("clinic_name")
        user_name_for_message = request.form.get("user_name_for_message")

        if not username or not password:
            flash("Username and password are required", "error")
            return render_template("register.html")

        try:
            # Register user with Supabase Auth
            auth_response = supabase.auth.sign_up({
                "email": f"{username}@example.com",  # Supabase requires email
                "password": password,
                "options": {
                    "data": {
                        "username": username,
                        "clinic_name": clinic_name,
                        "user_name_for_message": user_name_for_message
                    }
                }
            })

            if not auth_response.user:
                flash("Registration failed", "error")
                return render_template("register.html")

            # Create user profile in database
            db_manager = DatabaseManager("system", app.cipher_suite)
            success = db_manager.create_user(
                user_id=auth_response.user.id,
                username=username,
                clinic_name=clinic_name,
                user_name_for_message=user_name_for_message,
                appointment_types=[],
                appointment_types_data=[]
            )
            
            if not success:
                # Rollback auth creation if profile creation fails
                supabase.auth.admin.delete_user(auth_response.user.id)
                flash("Failed to create user profile", "error")
                return render_template("register.html")

            # Create user object and log in
            user = User(
                user_id=auth_response.user.id,
                username=username,
                clinic_name=clinic_name,
                user_name_for_message=user_name_for_message
            )
            login_user(user)
            flash("Registration successful!", "success")
            return redirect(url_for("index"))

        except Exception as e:
            logging.error(f"Error during registration: {e}", exc_info=True)
            flash("An error occurred during registration", "error")
            return render_template("register.html")

    return render_template("register.html")


# Add Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Username and password are required", "error")
            return render_template("login.html")

        try:
            # Authenticate with Supabase
            auth_response = supabase.auth.sign_in_with_password({
                "email": f"{username}@example.com",
                "password": password
            })

            if not auth_response.user:
                flash("Invalid username or password", "error")
                return render_template("login.html")

            # Get user profile from database
            db_manager = DatabaseManager("system", app.cipher_suite)
            user_data = db_manager.get_user_by_id(auth_response.user.id)
            
            if not user_data:
                flash("User profile not found", "error")
                return render_template("login.html")

            # Create user object and log in
            user = User.from_dict(user_data)
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for("index"))

        except Exception as e:
            logging.error(f"Error during login: {e}", exc_info=True)
            flash("An error occurred during login", "error")
            return render_template("login.html")

    return render_template("login.html")


# Add Logout Route
@app.route("/logout")
@login_required  # User must be logged in to log out
def logout():
    try:
        # Sign out from Supabase
        supabase.auth.sign_out()
        # Log out from Flask-Login
        logout_user()
        flash("Logged out successfully", "success")
    except Exception as e:
        logging.error(f"Error during logout: {e}", exc_info=True)
        flash("An error occurred during logout", "error")
    return redirect(url_for("login"))


@app.route("/slots", methods=["GET"])
@login_required
def slots():
    user_provider_manager, user_waitlist_manager, user_slot_manager = get_user_managers(current_user.username)
    providers = user_provider_manager.get_providers()
    all_slots = user_slot_manager.get_cancelled_slots()
    
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
            all_patients = user_waitlist_manager.get_patients()
            slot_duration = int(slot_for_match.get("duration", 0))
            slot_provider = slot_for_match.get("provider", "").lower()
            
            slot_date_str = slot_for_match.get("date")
            slot_period = slot_for_match.get("slot_period", "").upper()
            slot_dt = None
            if isinstance(slot_date_str, str):
                try:
                    slot_dt = datetime.strptime(slot_date_str, "%Y-%m-%d")
                except ValueError:
                    logging.warning(f"Could not parse slot_date '{slot_date_str}' for matching in /slots")
            elif isinstance(slot_date_str, datetime):
                slot_dt = slot_date_str

            logging.info(f"Slot requirements - Duration: {slot_duration}, Provider: {slot_provider}, Date: {slot_dt}, Period: {slot_period}")

            for patient in all_patients:
                if patient.get("status") != "waiting":
                    logging.info(f"Patient {patient.get('id')} skipped: Status is {patient.get('status')} (not waiting)")
                    continue

                patient_duration = int(patient.get("duration", 0))
                if patient_duration > slot_duration:
                    logging.info(f"Patient {patient.get('id')} skipped: Duration mismatch (patient: {patient_duration} > slot: {slot_duration})")
                    continue

                patient_provider_pref = patient.get("provider", "no preference").lower()
                if patient_provider_pref != "no preference" and patient_provider_pref != slot_provider:
                    logging.info(f"Patient {patient.get('id')} skipped: Provider mismatch (patient: '{patient_provider_pref}' != slot: '{slot_provider}')")
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


# Initialize managers
# Create user-specific paths for data files
def get_user_data_path(username, filename):
    """Get path to a user-specific data file"""
    user_dir = os.path.join(USERS_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, filename)


# Modify Index Route (Example of protecting and using current_user)
@app.route("/", methods=["GET"])
@login_required  # Protect the main page
def index():
    logging.debug(f"Entering index route for user: {current_user.username if current_user.is_authenticated else 'Not authenticated'}")
    logging.debug(f"Session contents: {dict(session)}")
    
    try:
        logging.info("Getting user managers...")
        user_provider_manager, user_waitlist_manager, user_slot_manager = get_user_managers(current_user.username)
        logging.info("Got user managers successfully")

        logging.info("Getting providers...")
        providers = user_provider_manager.get_providers()
        logging.info(f"Got {len(providers)} providers")

        logging.info("Getting patients...")
        waitlist = user_waitlist_manager.get_patients()
        logging.info(f"Got {len(waitlist)} patients")

        appointment_types = current_user.appointment_types or []
        appointment_types_data = current_user.appointment_types_data or []

        logging.info("Getting cancelled slots...")
        all_slots = user_slot_manager.get_cancelled_slots()
        logging.info(f"Got {len(all_slots)} cancelled slots")
        slot_map = {s['id']: s for s in all_slots}

        # Augment patient data with proposed slot details if pending
        for patient in waitlist:
             if patient.get("status") == "pending" and patient.get("proposed_slot_id"):
                 proposed_slot = slot_map.get(patient["proposed_slot_id"])
                 if proposed_slot:
                     # Format date if it's an object
                     slot_date_display = proposed_slot.get("date")
                     if isinstance(slot_date_display, datetime):
                         slot_date_display = slot_date_display.strftime('%a, %b %d') # Example format

                     patient["proposed_slot_details"] = f"Slot on {slot_date_display} ({proposed_slot.get('slot_period', '')}) w/ {proposed_slot.get('provider')}"
                 else:
                     patient["proposed_slot_details"] = "Proposed slot details unavailable"

        # Prepare duration map
        duration_map = {
            item["appointment_type"].lower().replace(" ", "_"): item["durations"]
            for item in appointment_types_data
            if "appointment_type" in item and "durations" in item
        }

        # Sorting
        def sort_key_waitlist(p):
            status_order = {'pending': 0, 'waiting': 1}
            wait_minutes = wait_time_to_minutes(p.get('wait_time', '0 minutes'))
            return (status_order.get(p.get('status', 'waiting'), 99), -wait_minutes)

        sorted_waitlist = sorted(waitlist, key=sort_key_waitlist)

        if not providers:
            flash("Please add Provider names via settings to proceed", "warning")

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
        logging.error(f"Exception in index route: {str(e)}", exc_info=True)
        flash(f"An error occurred while loading the main page: {str(e)}", "danger")
        return "<h1>An error occurred</h1><p>Please check the server logs.</p>", 500


@app.route("/add_patient", methods=["POST"])
@login_required
def add_patient():
    try:  # Main try block for the whole route
        # Get user-specific managers
        _, user_waitlist_manager, _ = get_user_managers(current_user.username)

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
        user_waitlist_manager.add_patient(
            name=name,
            phone=phone,
            email=email,
            reason=reason,
            urgency=urgency,
            appointment_type=appointment_type,
            duration=duration,
            provider=provider,
            availability=availability_prefs,
            availability_mode=availability_mode,
        )

        flash("Patient added successfully.", "success")

    except Exception as e:  # This except matches the initial try
        logging.error(
            f"Error in add_patient route for user {current_user.id}: {e}", exc_info=True
        )
        flash("An unexpected error occurred while adding the patient.", "danger")

    # This return is outside the try/except block
    return redirect(url_for("index") + "#add-patient-form")


@app.route("/remove_patient/<patient_id>", methods=["POST"])
@login_required
def remove_patient(patient_id):
    """Remove a patient from the waitlist"""
    _, user_waitlist_manager, _ = get_user_managers(current_user.username)
    success = user_waitlist_manager.remove_patient(patient_id)
    if success:
        flash("Patient removed successfully", "success")
    else:
        flash("Error removing patient", "danger")
    return redirect(url_for("index") + "#waitlist-table")


@app.route("/update_patient/<patient_id>", methods=["POST"])
@login_required
def update_patient(patient_id):
    """Update a patient's information"""
    _, user_waitlist_manager, _ = get_user_managers(current_user.username)
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
    success = user_waitlist_manager.update_patient(
        patient_id=patient_id, name=name, phone=phone, email=email, provider=provider,
        appointment_type=appointment_type, duration=duration, urgency=urgency, reason=reason,
        availability=availability, availability_mode=availability_mode)
    if success:
        flash("Patient updated successfully", "success")
    else:
        flash("Error updating patient", "danger")
    return redirect(url_for("index"))


@app.route("/add_cancelled_appointment", methods=["POST"])
@login_required
def add_cancelled_appointment():
    """Add a new cancelled appointment (open slot)"""
    _, _, user_slot_manager = get_user_managers(current_user.username)
    provider_id = request.form.get("provider")
    slot_date = request.form.get("date")
    slot_time_str = request.form.get("time")
    duration = request.form.get("duration")
    notes = request.form.get("notes", "")
    slot_period = "AM"
    if slot_time_str:
        try:
            time_obj = datetime.strptime(slot_time_str, "%H:%M").time()
            if time_obj.hour >= 12: slot_period = "PM"
        except ValueError:
            flash("Invalid time format entered.", "danger")
            return redirect(url_for("slots"))
    else:
        flash("Time is required.", "danger")
        return redirect(url_for("slots"))
    if not all([provider_id, slot_date, slot_time_str, duration]):
        flash("All required fields must be filled", "danger")
        return redirect(url_for("slots"))
    success = user_slot_manager.add_cancelled_slot(
        provider_id=provider_id,
        date=slot_date,
        time=slot_time_str,
        duration=duration,
        notes=notes
    )
    if success:
        flash("Open slot added successfully", "success")
    else:
        flash("Error adding open slot", "danger")
    return redirect(url_for("slots"))


@app.route("/remove_cancelled_slot/<appointment_id>", methods=["POST"])
@login_required
def remove_cancelled_slot(appointment_id):
    """Remove a cancelled appointment (open slot)"""
    _, _, user_slot_manager = get_user_managers(current_user.username)
    success = user_slot_manager.remove_cancelled_slot(appointment_id)
    if success:
        flash("Open slot removed successfully", "success")
    else:
        flash("Error removing open slot", "danger")
    return redirect(url_for("slots"))


@app.route("/update_cancelled_slot/<appointment_id>", methods=["POST"])
@login_required
def update_cancelled_slot(appointment_id):
    """Update a cancelled appointment (open slot)"""
    _, _, user_slot_manager = get_user_managers(current_user.username)
    
    # Log the incoming request data
    logging.info(f"Updating slot {appointment_id} with form data: {request.form}")
    
    provider = request.form.get("provider")
    slot_date = request.form.get("date")
    slot_time_str = request.form.get("time")
    duration = request.form.get("duration")
    notes = request.form.get("notes", "")
    
    if not all([provider, slot_date, slot_time_str, duration]):
        missing_fields = [f for f, v in [("provider", provider), ("date", slot_date), 
                                       ("time", slot_time_str), ("duration", duration)] if not v]
        logging.error(f"Missing required fields: {missing_fields}")
        flash("All required fields must be filled", "danger")
        return redirect(url_for("slots"))
        
    # Validate time format
    try:
        # Try parsing the time to validate format
        time_obj = datetime.strptime(slot_time_str, "%H:%M").time()
        # Ensure the time is in HH:MM format
        slot_time_str = time_obj.strftime("%H:%M")
        logging.info(f"Validated time format: {slot_time_str}")
    except ValueError as e:
        logging.error(f"Invalid time format: {slot_time_str}, error: {str(e)}")
        flash("Invalid time format entered. Please use HH:MM format (e.g., 09:30).", "danger")
        return redirect(url_for("slots"))
    
    try:
        # Log the data being sent to update_cancelled_slot
        update_data = {
            "provider": provider,
            "date": slot_date,
            "time": slot_time_str,
            "duration": duration,
            "notes": notes
        }
        logging.info(f"Attempting to update slot with data: {update_data}")
        
        success = user_slot_manager.update_cancelled_slot(
            slot_id=appointment_id,
            **update_data
        )
        
        if success:
            logging.info(f"Successfully updated slot {appointment_id}")
            flash("Open slot updated successfully", "success")
        else:
            logging.error(f"Failed to update slot {appointment_id}")
            flash("Error updating open slot", "danger")
    except Exception as e:
        logging.error(f"Exception while updating slot {appointment_id}: {str(e)}", exc_info=True)
        flash("Error updating open slot", "danger")
        
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
    _, user_waitlist_manager, user_slot_manager = get_user_managers(current_user.username)
    try:
        patient = user_waitlist_manager.get_patient(patient_id)
        patient_name = patient.get("name", "Unknown") if patient else "Unknown"
        slot_marked = user_slot_manager.mark_slot_as_pending(slot_id, patient_id, patient_name)
        patient_marked = user_waitlist_manager.mark_patient_as_pending(patient_id, slot_id)
        if slot_marked and patient_marked:
            flash("Slot proposed and marked as pending confirmation.", "info")
            session.pop("current_appointment_id", None)
        elif not slot_marked:
             flash("Error marking slot as pending. It might be already taken or not found.", "danger")
             user_waitlist_manager.cancel_patient_proposal(patient_id)
        elif not patient_marked:
             flash("Error marking patient as pending. They might not be waiting or not found.", "danger")
             user_slot_manager.cancel_slot_proposal(slot_id)
        else:
             flash("Error marking slot or patient as pending. Please check logs.", "danger")
    except Exception as e:
        logging.error(f"Error proposing slot {slot_id} to patient {patient_id}: {e}", exc_info=True)
        flash("An unexpected error occurred while proposing the slot.", "danger")
        try:
            user_slot_manager.cancel_slot_proposal(slot_id)
            user_waitlist_manager.cancel_patient_proposal(patient_id)
        except Exception as revert_e:
            logging.error(f"Error reverting state during proposal error: {revert_e}")
    redirect_url = request.referrer or url_for('index')
    if '/api/' in redirect_url or '/propose_slot/' in redirect_url: redirect_url = url_for('index')
    return redirect(redirect_url)


@app.route("/confirm_booking/<slot_id>/<patient_id>", methods=["POST"])
@login_required
def confirm_booking(slot_id, patient_id):
    """Confirms the booking, removing the patient and the slot."""
    _, user_waitlist_manager, user_slot_manager = get_user_managers(current_user.username)
    # try:
    slot = user_slot_manager.get_cancelled_slots()
    slot = next((s for s in slot if s.get('id') == slot_id), None)
    patient = user_waitlist_manager.get_patient(patient_id)
    if not slot or slot.get("status") != "pending" or slot.get("proposed_patient_id") != patient_id:
        flash("Error confirming: Slot not found, not pending, or proposed to a different patient.", "danger")
        return redirect(request.referrer or url_for('index'))
    if not patient or patient.get("status") != "pending" or patient.get("proposed_slot_id") != slot_id:
            flash("Error confirming: Patient not found, not pending, or proposed for a different slot.", "danger")
            return redirect(request.referrer or url_for('index'))
    patient_removed = user_waitlist_manager.remove_patient(patient_id)
    slot_removed = user_slot_manager.remove_slot(slot_id)
    if patient_removed and slot_removed:
        flash("Booking confirmed. Patient removed from waitlist and slot closed.", "success")
    else:
        flash("Error confirming booking during removal. Patient or slot may not have been fully removed.", "danger")
    # except Exception as e:
      #  logging.error(f"Error confirming booking for slot {slot_id} / patient {patient_id}: {e}", exc_info=True)
      #  flash("An unexpected error occurred while confirming the booking.", "danger")
    return redirect(url_for("index"))


@app.route("/cancel_proposal/<slot_id>/<patient_id>", methods=["POST"])
@login_required
def cancel_proposal(slot_id, patient_id):
    """Cancels a pending proposal, making the slot and patient available again."""
    _, user_waitlist_manager, user_slot_manager = get_user_managers(current_user.username)
    # try:
    slot = user_slot_manager.get_cancelled_slots()
    slot = next((s for s in slot if s.get('id') == slot_id), None)
    patient = user_waitlist_manager.get_patient(patient_id)
    if not slot or slot.get("status") != "pending" or slot.get("proposed_patient_id") != patient_id:
        flash("Error cancelling: Slot not found, not pending, or proposed to a different patient.", "warning")
        return redirect(request.referrer or url_for('index'))
    if not patient or patient.get("status") != "pending" or patient.get("proposed_slot_id") != slot_id:
            flash("Error cancelling: Patient not found, not pending, or proposed for a different slot.", "warning")
            return redirect(request.referrer or url_for('index'))
    slot_reset = user_slot_manager.cancel_slot_proposal(slot_id)
    patient_reset = user_waitlist_manager.cancel_patient_proposal(patient_id)
    if slot_reset and patient_reset:
        flash("Proposal cancelled. Slot and patient are available again.", "info")
    else:
        flash("Error cancelling proposal state. Please check logs.", "danger")
    # except Exception as e:
        logging.error(f"Error cancelling proposal for slot {slot_id} / patient {patient_id}: {e}", exc_info=True)
        flash("An unexpected error occurred while cancelling the proposal.", "danger")
    redirect_url = request.referrer or url_for('index')
    if '/api/' in redirect_url or '/cancel_proposal/' in redirect_url: redirect_url = url_for('index')
    return redirect(redirect_url)


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
                user_provider_manager, user_waitlist_manager, _ = get_user_managers(current_user.username)
                stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_input = csv.DictReader(stream)
                if not csv_input.fieldnames:
                    flash("CSV file is empty or has no header.", "warning")
                    return redirect(url_for("index") + "#waitlist-table")
                
                required_fields = ["name", "phone"] # Basic required fields
                header = [h.lower().strip().replace(" ", "_") for h in csv_input.fieldnames]
                
                # Normalize fieldnames in the DictReader if possible or handle it row by row
                # For simplicity, we'll normalize expected keys when accessing row data.
                
                missing_req_fields = [rf for rf in required_fields if rf not in header]
                if missing_req_fields:
                    flash(f"CSV missing required columns: {', '.join(missing_req_fields)}.", "danger")
                    return redirect(url_for("index") + "#waitlist-table")

                patients_to_add = []
                added_count = 0
                skipped_count = 0
                
                # Pre-fetch existing patients to check for duplicates
                existing_patients_tuples = set((p['name'].lower(), p['phone']) for p in user_waitlist_manager.get_patients())
                
                # Define available appointment types and providers for validation
                valid_appointment_types = [apt['appointment_type'].lower().replace(' ', '_') for apt in (current_user.appointment_types_data or [])]
                valid_providers = [p['name'].lower() for p in user_provider_manager.get_providers()]
                valid_providers.append("no preference") # Allow "no preference"

                # Helpers for validation
                def validate_urgency(urg_val):
                    return urg_val.lower() if urg_val and urg_val.lower() in ["high", "medium", "low"] else "medium"
                def validate_appointment_type(appt_val):
                    appt_norm = appt_val.lower().replace(' ', '_') if appt_val else "custom"
                    return appt_norm if appt_norm in valid_appointment_types or appt_norm == "custom" else "custom"
                def validate_duration(dur_val):
                    return dur_val if dur_val and dur_val.isdigit() and int(dur_val) > 0 else "30"
                def validate_provider(prov_val):
                    prov_norm = prov_val.lower() if prov_val else "no preference"
                    return prov_norm if prov_norm in valid_providers else "no preference"

                has_availability_col = "availability" in header
                has_mode_col = "availability_mode" in header

                for row_index, row_raw in enumerate(csv_input):
                    # Normalize keys in the current row
                    row = {k.lower().strip().replace(" ", "_"): v for k,v in row_raw.items()}

                    csv_name = row.get("name", "").strip()
                    csv_phone = row.get("phone", "").strip()

                    if not csv_name or not csv_phone:
                        skipped_count += 1
                        logging.warning(f"Skipping CSV row {row_index+1}: Missing name or phone.")
                        continue
                    if (csv_name.lower(), csv_phone) in existing_patients_tuples:
                        skipped_count += 1
                        logging.info(f"Skipping CSV row {row_index+1}: Patient '{csv_name}' with phone '{csv_phone}' already exists.")
                        continue
                    
                    availability_data = {}
                    if has_availability_col:
                        availability_str = row.get("availability", "").strip()
                        if availability_str:
                            try:
                                loaded_avail = json.loads(availability_str)
                                if isinstance(loaded_avail, dict):
                                    availability_data = {k.capitalize(): v for k, v in loaded_avail.items() if isinstance(v, list) and k.capitalize() in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}
                            except json.JSONDecodeError:
                                logging.warning(f"Failed to parse availability JSON for {csv_name} (row {row_index+1}): '{availability_str}'")
                                # Fallback for simple comma-separated days (e.g., "Monday,Tuesday") implies AM/PM for those days
                                parsed_days = [d.strip().capitalize() for d in availability_str.split(',') if d.strip().capitalize() in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]]
                                if parsed_days: availability_data = {day: ["AM", "PM"] for day in parsed_days}
                    
                    availability_mode = "available"
                    if has_mode_col:
                        mode_raw = row.get("availability_mode", "").strip().lower()
                        if mode_raw in ["available", "unavailable"]: availability_mode = mode_raw

                    patient_timestamp_str = row.get("timestamp", "")
                    patient_timestamp = None
                    if patient_timestamp_str:
                        try: patient_timestamp = datetime.fromisoformat(patient_timestamp_str)
                        except ValueError:
                            try: patient_timestamp = datetime.strptime(patient_timestamp_str, "%m/%d/%Y %H:%M")
                            except ValueError: logging.warning(f"Could not parse timestamp '{patient_timestamp_str}' for {csv_name}")
                    
                    patients_to_add.append({
                        "name": csv_name,
                        "phone": csv_phone,
                        "email": row.get("email", ""),
                        "reason": row.get("reason", ""),
                        "urgency": validate_urgency(row.get("urgency", "medium")),
                        "appointment_type": validate_appointment_type(row.get("appointment_type")),
                        "duration": validate_duration(row.get("duration", "30")),
                        "provider": validate_provider(row.get("provider")),
                        "timestamp": patient_timestamp, # Can be None, add_patient handles it
                        "availability": availability_data,
                        "availability_mode": availability_mode
                    })
                    added_count += 1
                    existing_patients_tuples.add((csv_name.lower(), csv_phone))

                if patients_to_add:
                    for p_data in patients_to_add:
                        user_waitlist_manager.add_patient(**p_data)
                
                if added_count > 0 and skipped_count > 0:
                    flash(f"Successfully added {added_count} new patients. Skipped {skipped_count} duplicates or rows with missing info.", "success")
                elif added_count > 0:
                    flash(f"Successfully added {added_count} new patients from CSV.", "success")
                elif skipped_count > 0:
                    flash(f"No new patients added. Skipped {skipped_count} duplicates or rows with missing info.", "info")
                else:
                    flash("No patients added from CSV. Ensure file has data and correct headers (name, phone).", "info")

            except Exception as e:
                logging.error(f"Error processing patient CSV: {str(e)}", exc_info=True)
                flash(f"Error processing CSV file: {str(e)}", "danger")
        else:
            flash("Invalid file format. Please upload a .csv file.", "danger")
        return redirect(url_for("index") + "#waitlist-table")
    
    # For GET request, just render the index page (or a dedicated upload page if you create one)
    # Typically, CSV upload is part of another page, like index.html, which would have the form.
    # If you want a GET request to show a form, you'd render a template here.
    # For now, redirecting to index, assuming the form is there.
    return redirect(url_for("index") + "#csv-upload-section") # Assuming a section in index.html


@app.route("/api/find_matches_for_patient/<patient_id>")
@login_required
def api_find_matches_for_patient(patient_id):
    user_provider_manager, user_waitlist_manager, user_slot_manager = get_user_managers(
        current_user.username
    )

    patient = user_waitlist_manager.get_patient(patient_id)
    logging.info(f"Finding matches for patient {patient_id}: {patient}")

    if not patient:
        return jsonify({"error": "Patient not found"}), 404
    if patient.get("status", "waiting") != "waiting":
        return jsonify({"error": "Patient is not currently waiting", "status": patient.get("status")}), 400

    # Get all available slots (status 'available')
    all_slots = user_slot_manager.get_cancelled_slots()
    available_slots = [
        slot for slot in all_slots if slot.get("status", "available") == "available"
    ]
    logging.info(f"Found {len(available_slots)} available slots for patient {patient_id}")

    # Filter slots based on patient requirements
    matching_slots = []
    patient_duration = int(patient.get("duration", 0))
    patient_provider_pref = patient.get("provider", "no preference").lower()
    patient_availability = patient.get("availability", {})
    patient_availability_mode = patient.get("availability_mode", "available")

    logging.info(f"Patient requirements - Duration: {patient_duration}, Provider: {patient_provider_pref}, Availability Mode: {patient_availability_mode}")
    logging.info(f"Patient availability preferences: {patient_availability}")

    for slot in available_slots:
        # Check duration
        slot_duration = int(slot.get("duration", 0))
        if patient_duration > slot_duration:
            logging.info(f"Slot {slot.get('id')} rejected: Duration mismatch (slot: {slot_duration} < patient: {patient_duration})")
            continue

        # Check provider
        slot_provider = slot.get("provider", "").lower()
        if patient_provider_pref != "no preference" and patient_provider_pref != slot_provider:
            logging.info(f"Slot {slot.get('id')} rejected: Provider mismatch (slot: '{slot_provider}' != patient: '{patient_provider_pref}')")
            continue

        # Check availability
        slot_date_str = slot.get("date")
        slot_period = slot.get("slot_period", "").upper() # AM/PM

        slot_date = None
        if isinstance(slot_date_str, str):
            try:
                slot_date = datetime.strptime(slot_date_str, "%Y-%m-%d")
            except ValueError:
                logging.warning(f"Could not parse slot date '{slot_date_str}' for slot {slot.get('id')}")
                continue
        elif isinstance(slot_date_str, datetime):
            slot_date = slot_date_str
        else:
            logging.warning(f"Invalid slot date type '{type(slot_date_str)}' for slot {slot.get('id')}")
            continue

        if patient_availability: # Only check if patient specified preferences
            slot_weekday = slot_date.strftime("%A") # Full day name e.g. Monday
            day_periods = patient_availability.get(slot_weekday, []) # Patient's pref for this day

            is_available_on_day_period = slot_period in day_periods

            if patient_availability_mode == "available":
                # Patient must be explicitly available
                if not day_periods or not is_available_on_day_period:
                    logging.info(f"Slot {slot.get('id')} rejected: Availability mismatch (mode: available, day: {slot_weekday}, period: {slot_period}, prefs: {day_periods})")
                    continue
            else: # patient_availability_mode == "unavailable"
                # Patient must NOT be explicitly unavailable
                if day_periods and is_available_on_day_period:
                    logging.info(f"Slot {slot.get('id')} rejected: Availability mismatch (mode: unavailable, day: {slot_weekday}, period: {slot_period}, prefs: {day_periods})")
                    continue

        # If all checks pass, add the slot
        logging.info(f"Slot {slot.get('id')} matched for patient {patient_id}")
        matching_slots.append(slot)

    # Sort matching slots by date
    def sort_key(slot):
        date_str = slot.get("date")
        if isinstance(date_str, str):
            try:
                return datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                return datetime.max
        elif isinstance(date_str, datetime):
            return date_str
        return datetime.max

    matching_slots.sort(key=sort_key)

    logging.info(f"Returning {len(matching_slots)} matching slots for patient {patient_id}")
    # Return only necessary slot info for the modal
    result_slots = []
    for slot in matching_slots:
        slot_data = slot.copy()
        if isinstance(slot_data.get("date"), datetime):
            slot_data["date"] = slot_data["date"].strftime('%Y-%m-%d')
        result_slots.append(slot_data)

    return jsonify({"patient": patient, "matching_slots": result_slots})


@app.route("/providers", methods=["GET"])
@login_required
def list_providers():
    user_provider_manager, _, _ = get_user_managers(current_user.username)
    providers = user_provider_manager.get_providers()
    return render_template("providers.html", providers=providers)


@app.route("/add_provider", methods=["POST"])
@login_required
def add_provider():
    user_provider_manager, _, _ = get_user_managers(current_user.username)
    first_name = request.form.get("first_name")
    last_initial = request.form.get("last_initial", "")
    if not first_name:
        flash("Provider first name is required.", "warning")
    elif user_provider_manager.add_provider(first_name, last_initial):
        flash("Provider added successfully.", "success")
    else:
        flash("Provider already exists or could not be added.", "warning")
    return redirect(url_for("list_providers"))


@app.route("/remove_provider", methods=["POST"])
@login_required
def remove_provider():
    user_provider_manager, _, _ = get_user_managers(current_user.username)
    first_name = request.form.get("first_name")
    last_initial = request.form.get("last_initial", "")
    if not first_name:
        flash("Provider name not provided for removal.", "warning")
    elif user_provider_manager.remove_provider(first_name, last_initial):
        flash("Provider removed successfully.", "success")
    else:
        flash("Provider not found or could not be removed.", "danger")
    return redirect(url_for("list_providers"))


@app.route("/edit_patient/<patient_id>", methods=["GET"])
@login_required
def edit_patient(patient_id):
    user_provider_manager, user_waitlist_manager, _ = get_user_managers(current_user.username)
    patient = user_waitlist_manager.get_patient(patient_id)
    if not patient:
        flash("Patient not found.", "danger")
        return redirect(url_for("index"))
    
    providers = user_provider_manager.get_providers()
    # Ensure appointment_types and appointment_types_data are available for the form
    appointment_types = current_user.appointment_types or []
    appointment_types_data = current_user.appointment_types_data or []

    return render_template("edit_patient.html",
                           patient=patient,
                           providers=providers,
                           has_providers=len(providers) > 0,
                           appointment_types=appointment_types,
                           appointment_types_data=appointment_types_data)


@app.route("/save_user_data/<user_id>", methods=["POST"])
def save_user_data(user_id):
    data = request.json
    save_to_diff_store(user_id, data)
    return jsonify({"status": "success"})

@app.route("/load_user_data/<user_id>", methods=["GET"])
def load_user_data(user_id):
    data = load_from_diff_store(user_id)
    if data is not None:
        return jsonify(data)
    else:
        return jsonify({"error": "No data found"}), 404

@app.route("/debug/session")
def debug_session():
    if not app.debug:
        return "Debug route not available in production", 403
        
    session_info = {
        "session_id": session.sid if hasattr(session, 'sid') else 'No session ID',
        "session_contents": dict(session),
        "user_authenticated": current_user.is_authenticated,
        "user_id": current_user.id if current_user.is_authenticated else None,
        "session_permanent": session.permanent,
        "session_directory": app.config["SESSION_FILE_DIR"],
        "session_directory_exists": os.path.exists(app.config["SESSION_FILE_DIR"]),
        "session_files": os.listdir(app.config["SESSION_FILE_DIR"]) if os.path.exists(app.config["SESSION_FILE_DIR"]) else []
    }
    return jsonify(session_info)

@app.route("/debug/write_test")
def debug_write_test():
    test_path = os.path.join(USERS_DIR, "test_write.txt")
    try:
        with open(test_path, "w") as f:
            f.write("test")
        return f"Successfully wrote to {test_path}"
    except Exception as e:
        return f"Failed to write to {test_path}: {e}", 500

@app.route("/debug/list_user_files/<username>")
def debug_list_user_files(username):
    user_dir = os.path.join(USERS_DIR, username)
    if not os.path.exists(user_dir):
        return f"User directory {user_dir} does not exist.", 404
    files = os.listdir(user_dir)
    return jsonify({"user_dir": user_dir, "files": files})

@app.route("/debug/show_profile/<username>")
def debug_show_profile(username):
    user_file = os.path.join(USERS_DIR, username, "profile.json")
    if not os.path.exists(user_file):
        return f"Profile file {user_file} does not exist.", 404
    try:
        user_data = load_decrypted_json(user_file)
        return jsonify(user_data)
    except Exception as e:
        return f"Error reading profile: {e}", 500

if __name__ == "__main__":
    # Create session directory if it doesn't exist
    session_dir = os.path.join(DATA_DIR, "flask_sessions")
    try:
        os.makedirs(session_dir, exist_ok=True)
        logger.info(f"Created session directory at: {session_dir}")
    except Exception as e:
        logger.error(f"Error creating session directory: {e}")
        raise
          
    logger.info("Session configuration:")
    logger.info("SECRET_KEY is set: %s", bool(app.secret_key))
    logger.info("SESSION_TYPE: %s", app.config.get("SESSION_TYPE"))
    logger.info("SESSION_FILE_DIR: %s", app.config.get("SESSION_FILE_DIR"))
    logger.info("SESSION_PERMANENT: %s", app.config.get("SESSION_PERMANENT"))
    
    app.run(host='0.0.0.0', port=7860, debug=True)  # Enable debug mode temporarily
