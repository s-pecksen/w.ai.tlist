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
from datetime import datetime, date
import os
import csv
from io import StringIO
from src.managers import ProviderManager, PatientWaitlistManager, CancelledSlotManager
import logging
import json  # Needed for handling availability JSON in CSV upload
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)

import hashlib

# --- Flask App Initialization ---
app = Flask(__name__) # RESTORE this line
app.secret_key = os.urandom(24)  # Keep existing secret key

# Make sure to add this for flash messages to work
app.config["SESSION_TYPE"] = "filesystem"

# Add isinstance to Jinja globals
app.jinja_env.globals.update(isinstance=isinstance)
# Also add datetime to globals if needed elsewhere, otherwise passing it in context is fine
app.jinja_env.globals.update(datetime=datetime)

# Define paths
users_dir = os.path.join("data", "users")  # New directory for user JSON files

# Create users directory if it doesn't exist
os.makedirs(users_dir, exist_ok=True)


# Add this helper function to convert wait time to minutes
def wait_time_to_minutes(wait_time_str):
    total_minutes = 0
    if not isinstance(wait_time_str, str):  # Check for non-string input
        return 0

    remaining = wait_time_str  # Start with the full string

    if "days" in remaining:
        try:
            parts = remaining.split("days")
            days = int(parts[0].strip())
            total_minutes += days * 24 * 60  # INSIDE try
            # Update remaining string ONLY if days parsing succeeds
            if len(parts) > 1 and "," in parts[1]:
                remaining = parts[1].split(",")[1].strip()
            else:  # Handle cases like "X days" with no comma/hours/mins
                remaining = ""
        except (ValueError, IndexError):
            # Handle error: print a warning, keep original 'remaining' for next steps
            logging.warning(f"Warning: Could not parse days from '{wait_time_str}'.")
            # Don't reset remaining, let subsequent parsers try

    # Process hours from the potentially updated 'remaining' string
    if "hours" in remaining:
        try:
            parts = remaining.split("hours")
            hours_str = parts[0].strip()
            # Handle potential leading comma if days failed but hours exist
            if hours_str.startswith(","):
                hours_str = hours_str[1:].strip()
            hours = int(hours_str)
            total_minutes += hours * 60  # INSIDE try
            # Update remaining string ONLY if hours parsing succeeds
            if len(parts) > 1 and "," in parts[1]:
                remaining = parts[1].split(",")[1].strip()
            else:  # Handle "X hours" with no following minutes
                remaining = ""  # Successfully parsed 'X hours', nothing left for mins
        except (ValueError, IndexError):
            # Handle error: print warning, proceed to minutes with current 'remaining'
            logging.warning(f"Warning: Could not parse hours from '{remaining}'.")
            # No need to reset 'remaining', just let minute parsing try

    # Process minutes from the potentially updated 'remaining' string
    if "minutes" in remaining:
        try:
            minutes_str = remaining.split("minutes")[0].strip()
            # Handle potential leading comma
            if minutes_str.startswith(","):
                minutes_str = minutes_str[1:].strip()
            minutes = int(minutes_str)
            total_minutes += minutes
        except (ValueError, IndexError):
            # Handle error: print warning
            logging.warning(f"Warning: Could not parse minutes from '{remaining}'.")

    return total_minutes


# --- Login Manager Setup ---
login_manager = LoginManager()
login_manager.login_view = (
    "login"  # Redirect user to /login if they access a protected page
)
login_manager.login_message = None # Disable default "Please log in" message BEFORE init_app
login_manager.init_app(app) # Initialize the login manager AFTER setting config


# --- User Class ---
class User(UserMixin):
    def __init__(
        self,
        user_id,
        username,
        password_hash,
        clinic_name=None,
        user_name_for_message=None,
        appointment_types=None,
        appointment_types_data=None,
    ):
        self.id = user_id
        self.username = username
        self.password_hash = password_hash
        self.clinic_name = clinic_name or ""
        self.user_name_for_message = user_name_for_message or ""
        self.appointment_types = appointment_types or []
        self.appointment_types_data = appointment_types_data or []

    def check_password(self, password):
        return hashlib.md5(password.encode()).hexdigest() == self.password_hash

    def to_dict(self):
        """Convert user object to dictionary for JSON storage"""
        return {
            "id": self.id,
            "username": self.username,
            "password_hash": self.password_hash,
            "clinic_name": self.clinic_name,
            "user_name_for_message": self.user_name_for_message,
            "appointment_types": self.appointment_types,
            "appointment_types_data": self.appointment_types_data,
        }

    @classmethod
    def from_dict(cls, data):
        """Create user object from dictionary"""
        return cls(
            user_id=data.get("id"),
            username=data.get("username"),
            password_hash=data.get("password_hash"),
            clinic_name=data.get("clinic_name"),
            user_name_for_message=data.get("user_name_for_message"),
            appointment_types=data.get("appointment_types"),
            appointment_types_data=data.get("appointment_types_data"),
        )


# --- User Management Functions ---
def save_user(user):
    """Save user to JSON file"""
    os.makedirs(os.path.join(users_dir, user.username), exist_ok=True)
    user_file = os.path.join(users_dir, user.username, f"profile.json")
    with open(user_file, "w") as f:
        json.dump(user.to_dict(), f, indent=4)
    return True


def get_user_by_username(username):
    """Get user by username from JSON file"""
    user_file = os.path.join(users_dir, username, "profile.json")
    if not os.path.exists(user_file):
        return None
    try:
        with open(user_file, "r") as f:
            user_data = json.load(f)
        return User.from_dict(user_data)
    except Exception as e:
        logging.error(f"Error loading user {username}: {e}")
        return None


def get_user_by_id(user_id):
    """Get user by ID from JSON files"""
    # Since we don't have an index, we need to scan all user directories
    if not os.path.exists(users_dir):
        return None

    for username in os.listdir(users_dir):
        user_dir = os.path.join(users_dir, username)
        if os.path.isdir(user_dir):  # Make sure it's a directory
            profile_path = os.path.join(user_dir, "profile.json")
            if os.path.exists(profile_path):
                try:
                    with open(profile_path, "r") as f:
                        user_data = json.load(f)
                    if str(user_data.get("id")) == str(user_id):
                        return User.from_dict(user_data)
                except Exception as e:
                    logging.error(f"Error reading user file {profile_path}: {e}")
    return None


def username_exists(username):
    """Check if username exists"""
    user_dir = os.path.join(users_dir, username)
    return os.path.exists(user_dir)


# Flask-Login user loader callback
@login_manager.user_loader
def load_user(user_id):
    """Load user by ID"""
    # Since we don't have an index, we need to scan all user directories
    if not os.path.exists(users_dir):
        return None

    for username in os.listdir(users_dir):
        user_dir = os.path.join(users_dir, username)
        if os.path.isdir(user_dir):  # Make sure it's a directory
            profile_path = os.path.join(user_dir, "profile.json")
            if os.path.exists(profile_path):
                try:
                    with open(profile_path, "r") as f:
                        user_data = json.load(f)
                    if str(user_data.get("id")) == str(user_id):
                        return User(
                            user_id=user_data.get("id"),
                            username=user_data.get("username"),
                            password_hash=user_data.get("password_hash"),
                            clinic_name=user_data.get("clinic_name"),
                            user_name_for_message=user_data.get(
                                "user_name_for_message"
                            ),
                            appointment_types=user_data.get("appointment_types"),
                            appointment_types_data=user_data.get(
                                "appointment_types_data"
                            ),
                        )
                except Exception as e:
                    logging.error(f"Error reading user file {profile_path}: {e}")
    return None


# Add Registration Route
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        clinic_name = request.form.get("clinic_name")
        user_name = request.form.get("user_name")
        appointment_types_json = request.form.get("appointment_types_json", "[]")

        # Process appointment types
        appointment_types_data = []
        try:
            appointment_types_data = json.loads(appointment_types_json)
            # Extract just the type names for backward compatibility
            appt_types_list = [
                item["appointment_type"] for item in appointment_types_data
            ]
        except (json.JSONDecodeError, KeyError):
            appt_types_list = []

        if not username or not password:
            flash("Username and password are required.", "warning")
            return redirect(url_for("register"))

        if username_exists(username):
            flash("Username already exists. Please choose a different one.", "warning")
            return redirect(url_for("register"))

        # Create new user with a unique ID
        user_id_raw = username + password
        user_id = hashlib.md5(user_id_raw.encode()).hexdigest()
        password_hash = hashlib.md5(password.encode()).hexdigest()
        new_user = User(
            user_id=user_id,
            username=username,
            password_hash=password_hash,
            clinic_name=clinic_name,
            user_name_for_message=user_name,
            appointment_types=appt_types_list,  # Simple list for backward compatibility
            appointment_types_data=appointment_types_data,  # Full data with durations
        )

        try:
            # Create user directory
            user_dir = os.path.join(users_dir, username)
            os.makedirs(user_dir, exist_ok=True)

            # Save user profile
            save_user(new_user)

            # Create empty provider.csv file with header
            provider_file = os.path.join(user_dir, "provider.csv")
            with open(provider_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["name"])  # Write header

            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            logging.error(f"Error during registration: {e}", exc_info=True)
            flash("An error occurred during registration. Please try again.", "danger")
            return redirect(url_for("register"))

    return render_template("register.html")


# Add Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = get_user_by_username(username)

        if user and user.check_password(password):
            login_user(
                user, remember=request.form.get("remember")
            )  # Add 'remember me' functionality
            flash("Logged in successfully.", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")  # Need to create this template


# Add Logout Route
@app.route("/logout")
@login_required  # User must be logged in to log out
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# Initialize managers
# Create user-specific paths for data files
def get_user_data_path(username, filename):
    """Get path to a user-specific data file"""
    user_dir = os.path.join(users_dir, username)
    os.makedirs(user_dir, exist_ok=True)
    return os.path.join(user_dir, filename)


# Function to get user-specific managers
def get_user_managers(username):
    """Get managers initialized with user-specific data paths"""
    user_dir = os.path.join(users_dir, username)
    os.makedirs(user_dir, exist_ok=True)

    # Initialize managers with user-specific file paths
    user_provider_manager = ProviderManager(
        provider_file=get_user_data_path(username, "provider.csv")
    )
    user_waitlist_manager = PatientWaitlistManager(
        waitlist_file=get_user_data_path(username, "waitlist.csv")
    )
    user_slot_manager = CancelledSlotManager(
        slots_file=get_user_data_path(username, "cancelled.csv")
    )

    return user_provider_manager, user_waitlist_manager, user_slot_manager


# Global managers for routes that don't have current_user context yet
# These will be replaced with user-specific managers in protected routes
provider_manager = ProviderManager()
waitlist_manager = PatientWaitlistManager()
slot_manager = CancelledSlotManager()


# Modify Index Route (Example of protecting and using current_user)
@app.route("/", methods=["GET"])
@login_required  # Protect the main page
def index():
    logging.debug(f"Entering index route for user: {current_user.username}")
    try:
        user_provider_manager, user_waitlist_manager, user_slot_manager = get_user_managers(current_user.username)
        user_waitlist_manager.update_wait_times() # Update wait times on load

        providers = user_provider_manager.get_provider_list()
        waitlist = user_waitlist_manager.get_all_patients()
        appointment_types = current_user.appointment_types or []
        appointment_types_data = current_user.appointment_types_data or []

        # Fetch slot data to potentially display proposed slot info
        all_slots = user_slot_manager.get_all_slots()
        slot_map = {s['id']: s for s in all_slots}

        # Augment patient data with proposed slot details if pending
        for patient in waitlist:
             if patient.get("status") == "pending" and patient.get("proposed_slot_id"):
                 proposed_slot = slot_map.get(patient["proposed_slot_id"])
                 if proposed_slot:
                     # Format date if it's an object
                     slot_date_display = proposed_slot.get("slot_date")
                     if isinstance(slot_date_display, datetime):
                         slot_date_display = slot_date_display.strftime('%a, %b %d') # Example format

                     patient["proposed_slot_details"] = f"Slot on {slot_date_display} ({proposed_slot.get('slot_period', '')}) w/ {proposed_slot.get('provider')}"
                 else:
                     patient["proposed_slot_details"] = "Proposed slot details unavailable"


        # Prepare duration map (already exists)
        duration_map = {
            item["appointment_type"].lower().replace(" ", "_"): item["durations"]
            for item in appointment_types_data
            if "appointment_type" in item and "durations" in item
        }

        # Sorting (keep existing placeholder or implement actual sort)
        # Example: Sort by status (pending first), then wait time (descending)
        def sort_key_waitlist(p):
            status_order = {'pending': 0, 'waiting': 1}
            # Use the wait_time_to_minutes helper
            wait_minutes = wait_time_to_minutes(p.get('wait_time', '0 minutes'))
            return (status_order.get(p.get('status', 'waiting'), 99), -wait_minutes)

        sorted_waitlist = sorted(waitlist, key=sort_key_waitlist)


        if not providers:
            flash("Please add Provider names via settings to proceed", "warning")

        return render_template(
            "index.html",
            providers=providers,
            waitlist=sorted_waitlist, # Use sorted list
            has_providers=len(providers) > 0,
            appointment_types=appointment_types,
            appointment_types_data=appointment_types_data,
            duration_map=duration_map,
            # Pass current_user details needed for the proposal modal JS
            current_clinic_name=current_user.clinic_name or "our clinic",
            current_user_name=current_user.user_name_for_message or "the scheduling team"
        )
    except Exception as e:
        logging.error(
            f"Exception in index route for user {current_user.id}: {e}", exc_info=True
        )
        flash("An error occurred while loading the main page.", "danger")
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


@app.route("/slots")
@login_required
def slots():
    # Get user-specific managers
    user_provider_manager, user_waitlist_manager, user_slot_manager = get_user_managers(
        current_user.username
    )

    # Get data from managers
    providers = user_provider_manager.get_provider_list()
    has_providers = len(providers) > 0

    # Get cancelled appointments (open slots), including status
    # Assumes get_all_slots() now returns status and proposed_patient_id
    all_cancelled_appointments = user_slot_manager.get_all_slots()

    # Get all waitlist patients, including status
    # Assumes get_all_patients() now returns status and proposed_slot_id
    all_patients = user_waitlist_manager.get_all_patients()
    patient_map = {p["id"]: p for p in all_patients} # For easy lookup

    # Process cancelled appointments
    cancelled_appointments = []
    for appointment in all_cancelled_appointments:
        # Convert string dates to datetime objects
        if appointment.get("slot_date"):
            try:
                appointment["slot_date"] = datetime.strptime(
                    appointment["slot_date"], "%Y-%m-%d"
                )
            except (ValueError, TypeError):
                pass # Keep as is if conversion fails

        # Add proposed patient details if pending
        if appointment.get("status") == "pending" and appointment.get("proposed_patient_id"):
            proposed_patient = patient_map.get(appointment["proposed_patient_id"])
            appointment["proposed_patient_name"] = proposed_patient["name"] if proposed_patient else "Unknown"

        cancelled_appointments.append(appointment)


    # Sort by date (most recent first - changed to ascending)
    cancelled_appointments.sort(
        key=lambda x: x.get("slot_date", datetime.max), reverse=False
    )

    # Get eligible patients only if there's a current_appointment_id in the session
    eligible_patients = None
    current_appointment = None
    current_appointment_id = session.get("current_appointment_id")

    if current_appointment_id:
        # Find the current appointment in the processed list
        current_appointment = next((appt for appt in cancelled_appointments if appt.get("id") == current_appointment_id), None)

        if current_appointment and current_appointment.get("status") != "pending": # Only find matches for available slots
            # Get eligible patients for this appointment
            # Filter to only 'waiting' patients (not pending or scheduled)
            eligible_patients = [
                p for p in all_patients
                if p.get("status", "waiting") == "waiting" # Assume default status is 'waiting'
            ]

            # --- Further Filtering Logic (Example - adapt as needed) ---
            # 1. Provider Preference
            slot_provider_lower = current_appointment.get("provider", "").lower()
            eligible_patients = [
                p for p in eligible_patients
                if p.get("provider", "").lower() == "no preference" or
                   p.get("provider", "").lower() == slot_provider_lower
            ]

            # 2. Duration
            slot_duration = int(current_appointment.get("duration", 0))
            eligible_patients = [
                p for p in eligible_patients
                if int(p.get("duration", 0)) <= slot_duration
            ]

            # 3. Availability (using existing logic, check if needs update for 'pending')
            if current_appointment.get("slot_date"):
                slot_date_obj = current_appointment["slot_date"]
                slot_weekday = slot_date_obj.strftime("%A") # Full weekday name
                slot_period = current_appointment.get("slot_period", "").upper() # AM/PM

                filtered_by_avail = []
                for p in eligible_patients:
                    availability = p.get("availability", {})
                    mode = p.get("availability_mode", "available")

                    # Skip availability check if patient has no preference
                    if not availability:
                        filtered_by_avail.append(p)
                        continue

                    day_periods = availability.get(slot_weekday, []) # Get patient's periods for that day
                    is_available_on_day_period = slot_period in day_periods

                    if mode == "available":
                        # Must be explicitly available
                        if is_available_on_day_period:
                            filtered_by_avail.append(p)
                    else: # mode == "unavailable"
                        # Must NOT be explicitly unavailable
                        if not is_available_on_day_period:
                            filtered_by_avail.append(p)
                eligible_patients = filtered_by_avail
            # --- End Filtering Logic ---


    return render_template(
        "slots.html",
        providers=providers,
        has_providers=has_providers,
        cancelled_appointments=cancelled_appointments,
        eligible_patients=eligible_patients,
        current_appointment=current_appointment,
        # Pass user/clinic name for the proposal modal message template
        current_user_name=current_user.user_name_for_message or "the scheduling team",
        current_clinic_name=current_user.clinic_name or "our clinic"
    )


@app.route("/schedule_patient/<patient_id>", methods=["POST"])
def schedule_patient(patient_id):
    # Update wait times first
    waitlist_manager.update_wait_times()

    # Schedule the patient using manager
    if waitlist_manager.schedule_patient(patient_id):
        flash("Patient scheduled successfully.", "success")
    else:
        flash("Failed to schedule patient.", "danger")
    # Redirect back to the index page, focusing on the waitlist table
    return redirect(url_for("index") + "#waitlist-table")  # Added fragment


@app.route("/remove_patient/<patient_id>", methods=["POST"])
@login_required # Ensures current_user is available
def remove_patient(patient_id):
    # Get the correct user-specific managers
    _, user_waitlist_manager, _ = get_user_managers(current_user.username)

    # Call remove_patient on the USER-SPECIFIC manager instance
    if user_waitlist_manager.remove_patient(patient_id):
        flash("Patient removed successfully.", "success")
    else:
        # The improved logging in remove_patient will now indicate *why* it failed if it still does
        flash("Failed to remove patient.", "danger")
    # Redirect back to the index page, focusing on the waitlist table
    return redirect(url_for("index") + "#waitlist-table")


# Add these helper functions
def validate_appointment_type(value):
    # Updated valid types based on user request
    valid_types = [
        "hygiene",
        "recall",
        "resto",
        "x-ray",
        "np_spec",
        "spec_exam",
        "emergency_exam",
        "rct",
        "custom",
    ]
    value_str = str(value).lower().strip()
    # Defaulting to 'hygiene' as a common type if the provided one isn't valid
    return value_str if value_str in valid_types else "hygiene"


def validate_duration(value):
    # Use the updated list of durations from the HTML forms
    valid_durations = ["30", "60", "70", "90", "120"]
    return str(value) if str(value) in valid_durations else "30"


def validate_provider(value):
    # Get the list of valid providers from the provider manager
    # Now retrieves dictionaries [{'name': 'Provider Name'}]
    valid_providers_list = provider_manager.get_provider_list()
    valid_provider_names = ["no preference"] + [
        p.get("name", "").lower() for p in valid_providers_list
    ]

    # Convert empty string or None to 'no preference'
    provider_value_lower = (value or "").strip().lower()
    if not provider_value_lower or provider_value_lower == "no preference":
        return "no preference"

    # Check if the provided value is in our list (case-insensitive)
    if provider_value_lower in valid_provider_names:
        # Find the original casing from the manager's list
        for p_dict in valid_providers_list:
            if p_dict.get("name", "").lower() == provider_value_lower:
                return p_dict["name"]  # Return correctly cased name
        # Fallback if somehow not found after check (shouldn't happen)
        return value.strip()

    # Default to 'no preference' if not found
    return "no preference"


def validate_urgency(value):
    valid_urgency = ["low", "medium", "high"]
    return value.lower() if value.lower() in valid_urgency else "medium"


@app.route("/upload_csv", methods=["POST"])
def upload_csv():
    print("--- DEBUG: /upload_csv route hit ---")
    if not provider_manager.get_provider_list():
        flash("Please add providers before uploading patient data", "warning")
        return redirect(url_for("index"))

    if "csv_file" not in request.files:
        flash("No file selected for upload.", "warning")
        return redirect(url_for("index"))

    file = request.files["csv_file"]
    if file.filename == "":
        flash("No file selected for upload.", "warning")
        return redirect(url_for("index"))

    if file and file.filename.endswith(".csv"):
        try:
            stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
            reader = csv.DictReader(stream)
            added_count = 0
            skipped_count = 0
            required_columns = ["name", "phone"]  # Minimum required

            existing_patients_list = waitlist_manager.get_all_patients()
            existing_patients_set = {
                (p.get("name", "").strip(), p.get("phone", "").strip())
                for p in existing_patients_list
                if p.get("name") and p.get("phone")
            }
            print(
                f"--- DEBUG: Found {len(existing_patients_set)} existing patients for duplicate check ---"
            )

            patients_to_add = []
            headers = reader.fieldnames or []
            print(f"--- DEBUG: CSV Headers: {headers} ---")
            if not all(col in headers for col in required_columns):
                flash(
                    f'CSV must contain at least {", ".join(required_columns)} columns',
                    "danger",
                )
                return redirect(url_for("index"))

            print("--- DEBUG: Required columns check passed ---")
            has_availability_col = "availability" in headers
            has_mode_col = "availability_mode" in headers

            for row in reader:
                csv_name = row.get("name", "").strip()
                csv_phone = row.get("phone", "").strip()
                if not csv_name or not csv_phone:
                    print(
                        f"--- DEBUG: Skipping row due to missing name/phone: {row} ---"
                    )
                    skipped_count += 1
                    continue
                if (csv_name, csv_phone) in existing_patients_set:
                    print(
                        f"--- DEBUG: Skipping duplicate patient: {csv_name}, {csv_phone} ---"
                    )
                    skipped_count += 1
                    continue

                provider_value = row.get("provider", "")

                # --- Try parsing timestamp ---
                datetime_str = row.get("date_time_entered", "").strip()
                parsed_timestamp = None
                if datetime_str:
                    try:
                        # Combined parsing attempts
                        parsed_timestamp = datetime.fromisoformat(datetime_str)
                    except ValueError:
                        possible_formats = [
                            "%m/%d/%Y %H:%M:%S",
                            "%#m/%#d/%Y %#H:%M:%S",
                            "%m/%d/%y %I:%M %p",
                            "%m/%d/%Y %I:%M %p",
                        ]
                        for fmt in possible_formats:
                            try:
                                parsed_timestamp = datetime.strptime(datetime_str, fmt)
                                break
                            except ValueError:
                                continue
                        if not parsed_timestamp:
                            print(
                                f"--- DEBUG: Could not parse timestamp '{datetime_str}' for patient {csv_name} ---"
                            )

                # --- Parse availability from CSV ---
                # Expects availability column to contain JSON string like '{"Monday": ["AM", "PM"]}'
                # or potentially older format like comma-separated days ('Monday, Tuesday')
                availability_data = {}
                if has_availability_col:
                    availability_str = row.get("availability", "").strip()
                    if availability_str:
                        try:
                            # Try parsing as JSON first
                            loaded_avail = json.loads(availability_str)
                            if isinstance(loaded_avail, dict):
                                # Validate structure (ensure values are lists)
                                availability_data = {
                                    k: v
                                    for k, v in loaded_avail.items()
                                    if isinstance(v, list)
                                }
                            else:
                                print(
                                    f"--- DEBUG: Parsed availability JSON for {csv_name} is not a dict: '{availability_str}' ---"
                                )
                        except json.JSONDecodeError:
                            # Fallback: Try parsing as simple comma-separated days (implies full day availability)
                            # This is for backward compatibility; new uploads should use JSON.
                            print(
                                f"--- DEBUG: Failed to parse availability as JSON for {csv_name}, trying comma-separated: '{availability_str}' ---"
                            )
                            days_list = [
                                day.strip()
                                for day in availability_str.split(",")
                                if day.strip()
                            ]
                            if days_list:
                                # Assume AM and PM if parsed this old way
                                availability_data = {
                                    day: ["AM", "PM"] for day in days_list
                                }

                # --- Parse availability_mode from CSV ---
                # Defaults to 'available' if column missing or value invalid
                availability_mode = "available"
                if has_mode_col:
                    mode_raw = row.get("availability_mode", "").strip().lower()
                    if mode_raw in ["available", "unavailable"]:
                        availability_mode = mode_raw

                patients_to_add.append(
                    {
                        "name": csv_name,
                        "phone": csv_phone,
                        "email": row.get("email", ""),
                        "reason": row.get("reason", ""),
                        "urgency": validate_urgency(row.get("urgency", "medium")),
                        "appointment_type": validate_appointment_type(
                            row.get("appointment_type")
                        ),
                        "duration": validate_duration(row.get("duration", "30")),
                        "provider": validate_provider(provider_value),
                        "timestamp": parsed_timestamp,
                        "availability": availability_data,  # Pass parsed dict
                        "availability_mode": availability_mode,  # Pass parsed mode
                    }
                )
                added_count += 1
                existing_patients_set.add((csv_name, csv_phone))

            print(
                f"--- DEBUG: Finished reading rows. Added: {added_count}, Skipped: {skipped_count} ---"
            )

            if patients_to_add:
                print(
                    f"--- DEBUG: Adding {len(patients_to_add)} new patients to manager ---"
                )
                for p_data in patients_to_add:
                    # Extract specific args for manager method
                    patient_timestamp = p_data.pop("timestamp", None)
                    patient_availability = p_data.pop("availability", {})
                    patient_mode = p_data.pop("availability_mode", "available")
                    waitlist_manager.add_patient(
                        timestamp=patient_timestamp,
                        availability=patient_availability,
                        availability_mode=patient_mode,
                        **p_data,
                    )

            print("--- DEBUG: Finished adding patients to manager ---")
            # Update Flash Message (logic unchanged)
            if added_count > 0 and skipped_count > 0:
                flash(
                    f"Successfully added {added_count} new patients. Skipped {skipped_count} duplicates or rows with missing info.",
                    "success",
                )
            elif added_count > 0:
                flash(
                    f"Successfully added {added_count} new patients from CSV.",
                    "success",
                )
            elif skipped_count > 0:
                flash(
                    f"No new patients added. Skipped {skipped_count} duplicates or rows with missing info.",
                    "info",
                )
            else:
                flash("No patients added from CSV.", "info")

        except Exception as e:
            print(
                f"--- DEBUG: Exception caught in /upload_csv: {str(e)} ---"
            )  # Added print
            logging.error(
                f"Error processing patient CSV: {str(e)}", exc_info=True
            )  # Use logging.error
            flash(f"Error processing CSV file: {str(e)}", "danger")

    else:
        print(f"--- DEBUG: File format check failed for {file.filename} ---")
        flash("Invalid file format. Please upload a .csv file.", "danger")

    print("--- DEBUG: Reaching end of /upload_csv route ---")
    # Redirect back to the index page, focusing on the waitlist table after upload attempt
    return redirect(url_for("index") + "#waitlist-table")  # Added fragment


@app.route("/providers", methods=["GET"])
@login_required  # Add login requirement
def list_providers():
    # Get user-specific provider manager
    user_provider_manager, _, _ = get_user_managers(current_user.username)

    # Get providers from user-specific manager
    providers = user_provider_manager.get_provider_list()
    return render_template("providers.html", providers=providers)


@app.route("/providers/add", methods=["POST"])
@login_required  # Add login requirement
def add_provider():
    # Get user-specific provider manager
    user_provider_manager, _, _ = get_user_managers(current_user.username)

    first_name = request.form.get("first_name")
    last_initial = request.form.get("last_initial")

    if first_name:
        # Call add_provider on user-specific manager
        success = user_provider_manager.add_provider(first_name, last_initial)
        if success:
            flash("Provider added successfully", "success")
        else:
            flash("Provider already exists", "danger")
    else:
        flash("First name is required", "danger")

    # Redirect back to providers list
    return redirect(url_for("list_providers") + "#provider-list")  # Added fragment


@app.route("/providers/remove", methods=["POST"])
@login_required  # Add login requirement
def remove_provider():
    # Get user-specific provider manager
    user_provider_manager, _, _ = get_user_managers(current_user.username)

    first_name = request.form.get("first_name")
    last_initial = request.form.get("last_initial")

    if user_provider_manager.remove_provider(first_name, last_initial):
        flash("Provider removed successfully")
    else:
        flash("Provider not found")

    # Redirect back to providers list
    return redirect(url_for("list_providers") + "#provider-list")  # Added fragment


@app.route("/api/matching_slots/<patient_id>")
@login_required
def api_matching_slots(patient_id):
    """API endpoint to get slots matching a patient's requirements"""
    # Get user-specific managers
    user_provider_manager, user_waitlist_manager, user_slot_manager = get_user_managers(
        current_user.username
    )

    # Get the specific patient
    patient = user_waitlist_manager.get_patient(patient_id) # Assuming get_patient exists

    if not patient or patient.get("status", "waiting") != "waiting": # Ensure patient exists and is waiting
        return jsonify({"error": "Patient not found or not currently waiting"}), 404

    # Get all available slots (status 'available')
    # Assumes get_all_slots can filter or returns status
    all_slots = user_slot_manager.get_all_slots()
    available_slots = [
        slot for slot in all_slots if slot.get("status", "available") == "available"
    ]

    # Filter slots based on patient requirements
    matching_slots = []
    for slot in available_slots:
        # Skip slots that already have a matched patient (redundant if filtered above, but safe)
        # if slot.get("matched_patient_id") or slot.get("status") == 'pending':
        #    continue
        if slot.get("status", "available") != "available":
           continue


        # Check if duration matches
        patient_duration = int(patient.get("duration", 0))
        slot_duration = int(slot.get("duration", 0))
        if patient_duration > slot_duration:
            continue

        # Check if provider matches or patient has no preference
        patient_provider = patient.get("provider", "").lower()
        slot_provider = slot.get("provider", "").lower()
        if patient_provider != "no preference" and patient_provider and patient_provider != slot_provider: # Added check for non-empty patient_provider
            continue

        # Check availability if patient has specified availability
        patient_availability = patient.get("availability", {})
        slot_date_str = slot.get("slot_date") # Might be string or datetime object

        # Convert slot_date to datetime object if it's a string
        slot_date = None
        if isinstance(slot_date_str, str):
            try:
                slot_date = datetime.strptime(slot_date_str, "%Y-%m-%d")
            except ValueError:
                pass # Keep slot_date as None if parsing fails
        elif isinstance(slot_date_str, datetime):
             slot_date = slot_date_str # Use it directly if already datetime

        if patient_availability and slot_date:
            slot_weekday = slot_date.strftime("%A") # Full day name
            slot_period = slot.get("slot_period", "").upper() # AM/PM

            # Check if patient is available at this time
            availability_mode = patient.get("availability_mode", "available")
            # Ensure keys in patient_availability match the weekday format
            day_periods = patient_availability.get(slot_weekday, [])

            is_available_on_day_period = slot_period in day_periods

            if availability_mode == "available":
                # Patient specified when they ARE available
                if not day_periods or not is_available_on_day_period:
                    continue
            else: # availability_mode == "unavailable"
                # Patient specified when they are NOT available
                if day_periods and is_available_on_day_period:
                    continue
            # If we fall through, the patient is available for this slot based on their rules

        # If we got here, the slot matches
        matching_slots.append(slot)

    # Sort matching slots by date
    matching_slots.sort(key=lambda x: (datetime.strptime(x["slot_date"], "%Y-%m-%d") if isinstance(x.get("slot_date"), str) else x.get("slot_date", datetime.max)))


    return jsonify({"patient": patient, "matching_slots": matching_slots})


@app.route("/edit_patient/<patient_id>", methods=["GET"])
@login_required
def edit_patient(patient_id):
    # Get user-specific managers
    user_provider_manager, user_waitlist_manager, _ = get_user_managers(
        current_user.username
    )

    # Get the patient
    patient = user_waitlist_manager.get_patient(patient_id)
    if not patient:
        flash("Patient not found.", "danger")
        return redirect(url_for("index"))

    # Get providers
    providers = user_provider_manager.get_provider_list()

    # Get appointment types from user profile
    appointment_types = current_user.appointment_types or []
    appointment_types_data = current_user.appointment_types_data or []

    return render_template(
        "edit_patient.html",
        patient=patient,
        providers=providers,
        has_providers=len(providers) > 0,
        appointment_types=appointment_types,
        appointment_types_data=appointment_types_data,
    )


@app.route("/api/patient/<patient_id>")
@login_required
def api_get_patient(patient_id):
    """API endpoint to get patient data"""
    # Get user-specific managers
    _, user_waitlist_manager, _ = get_user_managers(current_user.username)

    # Get all patients and find the specific one
    patients = user_waitlist_manager.get_all_patients()
    patient = next((p for p in patients if p.get("id") == patient_id), None)

    if not patient:
        return jsonify({"error": "Patient not found"}), 404

    # Convert availability from JSON string to dict if needed
    if isinstance(patient.get("availability"), str):
        try:
            patient["availability"] = json.loads(patient["availability"])
        except (json.JSONDecodeError, TypeError):
            patient["availability"] = {}

    # Convert timestamp to string if it's a datetime object
    if isinstance(patient.get("timestamp"), datetime):
        patient["timestamp"] = patient["timestamp"].isoformat()

    return jsonify(patient)


@app.route("/update_patient/<patient_id>", methods=["POST"])
@login_required
def update_patient(patient_id):
    """Update a patient's information"""
    # Get user-specific managers
    _, user_waitlist_manager, _ = get_user_managers(current_user.username)

    # Get form data
    name = request.form.get("name")
    phone = request.form.get("phone")
    email = request.form.get("email", "")
    provider = request.form.get("provider")
    appointment_type = request.form.get("appointment_type")
    duration = request.form.get("duration")
    urgency = request.form.get("urgency")
    reason = request.form.get("reason", "")
    availability_mode = request.form.get("availability_mode", "available")

    # Build availability dictionary from form data
    availability = {}
    days = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    for day in days:
        am_key = f"avail_{day}_am"
        pm_key = f"avail_{day}_pm"
        periods = []
        if am_key in request.form:
            periods.append("AM")
        if pm_key in request.form:
            periods.append("PM")
        if periods:  # Only add days with at least one period selected
            availability[day.capitalize()] = periods

    # Update the patient
    success = user_waitlist_manager.update_patient(
        patient_id=patient_id,
        name=name,
        phone=phone,
        email=email,
        provider=provider,
        appointment_type=appointment_type,
        duration=duration,
        urgency=urgency,
        reason=reason,
        availability=availability,
        availability_mode=availability_mode,
    )

    if success:
        flash("Patient updated successfully", "success")
    else:
        flash("Error updating patient", "danger")

    return redirect(url_for("index"))


@app.route("/add_cancelled_appointment", methods=["POST"])
@login_required
def add_cancelled_appointment():
    """Add a new cancelled appointment (open slot)"""
    # Get user-specific managers
    _, _, user_slot_manager = get_user_managers(current_user.username)

    # Get form data
    provider = request.form.get("provider")
    slot_date = request.form.get("slot_date")
    slot_time = request.form.get("slot_time")
    slot_period = request.form.get("slot_period")
    duration = request.form.get("duration")
    notes = request.form.get("notes", "")

    # Validate required fields
    if not all([provider, slot_date, slot_time, slot_period, duration]):
        flash("All required fields must be filled", "danger")
        return redirect(url_for("slots"))

    # Add the slot
    success = user_slot_manager.add_slot(
        provider=provider,
        slot_date=slot_date,
        slot_time=slot_time,
        slot_period=slot_period,
        duration=duration,
        notes=notes,
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
    # Get user-specific managers
    _, _, user_slot_manager = get_user_managers(current_user.username)

    # Remove the slot
    success = user_slot_manager.remove_slot(appointment_id)

    if success:
        flash("Open slot removed successfully", "success")
    else:
        flash("Error removing open slot", "danger")

    return redirect(url_for("slots"))


@app.route("/update_cancelled_slot/<appointment_id>", methods=["POST"])
@login_required
def update_cancelled_slot(appointment_id):
    """Update a cancelled appointment (open slot)"""
    # Get user-specific managers
    _, _, user_slot_manager = get_user_managers(current_user.username)

    # Get form data
    provider = request.form.get("provider")
    slot_date = request.form.get("slot_date")
    slot_time = request.form.get("slot_time")
    slot_period = request.form.get("slot_period")
    duration = request.form.get("duration")
    notes = request.form.get("notes", "")

    # Validate required fields
    if not all([provider, slot_date, slot_time, slot_period, duration]):
        flash("All required fields must be filled", "danger")
        return redirect(url_for("slots"))

    # Update the slot
    success = user_slot_manager.update_slot(
        slot_id=appointment_id,
        provider=provider,
        slot_date=slot_date,
        slot_time=slot_time,
        slot_period=slot_period,
        duration=duration,
        notes=notes,
    )

    if success:
        flash("Open slot updated successfully", "success")
    else:
        flash("Error updating open slot", "danger")

    return redirect(url_for("slots"))


@app.route("/find_matches_for_appointment/<appointment_id>", methods=["POST"])
@login_required
def find_matches_for_appointment(appointment_id):
    """Find matching patients for a cancelled appointment"""
    # Store the appointment ID in the session
    session["current_appointment_id"] = appointment_id

    # Redirect to the slots page, which will show eligible patients
    return redirect(url_for("slots") + "#eligible-patients-section")


@app.route("/propose_slot/<slot_id>/<patient_id>", methods=["POST"])
@login_required
def propose_slot(slot_id, patient_id):
    """Marks a slot and patient as pending confirmation."""
    user_provider_manager, user_waitlist_manager, user_slot_manager = get_user_managers(current_user.username)

    try:
        # Get patient name for the slot record
        patient = user_waitlist_manager.get_patient(patient_id)
        patient_name = patient.get("name", "Unknown") if patient else "Unknown"

        # Use the new manager methods
        slot_marked = user_slot_manager.mark_as_pending(slot_id, patient_id, patient_name)
        patient_marked = user_waitlist_manager.mark_as_pending(patient_id, slot_id)

        if slot_marked and patient_marked:
            flash("Slot proposed and marked as pending confirmation.", "info")
            session.pop("current_appointment_id", None) # Clear session if coming from slots page
        elif not slot_marked:
             flash("Error marking slot as pending. It might be already taken or not found.", "danger")
             # Attempt to revert patient status if slot marking failed
             user_waitlist_manager.cancel_proposal(patient_id)
        elif not patient_marked:
             flash("Error marking patient as pending. They might not be waiting or not found.", "danger")
             # Attempt to revert slot status if patient marking failed
             user_slot_manager.cancel_proposal(slot_id)
        else:
             # Should not happen if both failed individually, but good fallback
            flash("Error marking slot or patient as pending. Please check logs.", "danger")


    except Exception as e:
        logging.error(f"Error proposing slot {slot_id} to patient {patient_id}: {e}", exc_info=True)
        flash("An unexpected error occurred while proposing the slot.", "danger")
        # Attempt to revert state on unexpected error
        try:
            user_slot_manager.cancel_proposal(slot_id)
            user_waitlist_manager.cancel_proposal(patient_id)
        except Exception as revert_e:
            logging.error(f"Error reverting state during proposal error: {revert_e}")


    # Determine redirect based on referrer or a parameter?
    # For now, redirect to index, assuming proposal might happen there too.
    # TODO: Make redirect smarter?
    redirect_url = request.referrer or url_for('index')
    # Avoid redirecting back to the API endpoint itself
    if '/api/' in redirect_url:
        redirect_url = url_for('index')

    return redirect(redirect_url)


@app.route("/confirm_booking/<slot_id>/<patient_id>", methods=["POST"])
@login_required
def confirm_booking(slot_id, patient_id):
    """Confirms the booking, removing the patient and the slot."""
    user_provider_manager, user_waitlist_manager, user_slot_manager = get_user_managers(current_user.username)

    try:
        # Verify both are in pending state and match each other
        slot = user_slot_manager.get_all_slots() # Re-fetch fresh data
        slot = next((s for s in slot if s.get('id') == slot_id), None)
        patient = user_waitlist_manager.get_patient(patient_id)

        if not slot or slot.get("status") != "pending" or slot.get("proposed_patient_id") != patient_id:
            flash("Error confirming: Slot not found, not pending, or proposed to a different patient.", "danger")
            return redirect(request.referrer or url_for('index'))

        if not patient or patient.get("status") != "pending" or patient.get("proposed_slot_id") != slot_id:
             flash("Error confirming: Patient not found, not pending, or proposed for a different slot.", "danger")
             return redirect(request.referrer or url_for('index'))


        # --- Action: Remove patient and slot ---
        patient_removed = user_waitlist_manager.remove_patient(patient_id)
        slot_removed = user_slot_manager.remove_slot(slot_id)
        # --- End Action ---

        # --- Alternative Action: Mark as scheduled/filled (Comment out removal above if using this) ---
        # patient_confirmed = user_waitlist_manager.mark_as_scheduled(patient_id)
        # slot_confirmed = user_slot_manager.mark_as_filled(slot_id)
        # if patient_confirmed and slot_confirmed:
        #      flash("Booking confirmed. Patient marked as scheduled and slot filled.", "success")
        # else:
        #      flash("Error confirming booking status updates. Please check logs.", "danger")
        # --- End Alternative Action ---

        # Check result of removal action
        if patient_removed and slot_removed:
            flash("Booking confirmed. Patient removed from waitlist and slot closed.", "success")
        else:
            # This case implies an issue with the removal itself, maybe file access?
            flash("Error confirming booking during removal. Patient or slot may not have been fully removed.", "danger")


    except Exception as e:
        logging.error(f"Error confirming booking for slot {slot_id} / patient {patient_id}: {e}", exc_info=True)
        flash("An unexpected error occurred while confirming the booking.", "danger")

    # Redirect to index after confirmation
    return redirect(url_for("index"))


@app.route("/cancel_proposal/<slot_id>/<patient_id>", methods=["POST"])
@login_required
def cancel_proposal(slot_id, patient_id):
    """Cancels a pending proposal, making the slot and patient available again."""
    user_provider_manager, user_waitlist_manager, user_slot_manager = get_user_managers(current_user.username)

    try:
         # Verify both are in pending state and match each other before cancelling
        slot = user_slot_manager.get_all_slots() # Re-fetch fresh data
        slot = next((s for s in slot if s.get('id') == slot_id), None)
        patient = user_waitlist_manager.get_patient(patient_id)

        if not slot or slot.get("status") != "pending" or slot.get("proposed_patient_id") != patient_id:
            flash("Error cancelling: Slot not found, not pending, or proposed to a different patient.", "warning")
            # Still try to reset patient just in case? Or just return?
            # user_waitlist_manager.cancel_proposal(patient_id) # Maybe?
            return redirect(request.referrer or url_for('index'))

        if not patient or patient.get("status") != "pending" or patient.get("proposed_slot_id") != slot_id:
             flash("Error cancelling: Patient not found, not pending, or proposed for a different slot.", "warning")
             # Still try to reset slot just in case? Or just return?
             # user_slot_manager.cancel_proposal(slot_id) # Maybe?
             return redirect(request.referrer or url_for('index'))


        # Use the new manager methods
        slot_reset = user_slot_manager.cancel_proposal(slot_id)
        patient_reset = user_waitlist_manager.cancel_proposal(patient_id)

        if slot_reset and patient_reset:
            flash("Proposal cancelled. Slot and patient are available again.", "info")
        else:
            # This suggests one of the cancel methods failed internally
            flash("Error cancelling proposal state. Please check logs.", "danger")

    except Exception as e:
        logging.error(f"Error cancelling proposal for slot {slot_id} / patient {patient_id}: {e}", exc_info=True)
        flash("An unexpected error occurred while cancelling the proposal.", "danger")

    # Redirect back to where the user was (likely slots page or index page)
    redirect_url = request.referrer or url_for('index')
    if '/api/' in redirect_url: # Avoid redirecting back to api
        redirect_url = url_for('index')
    return redirect(redirect_url)


@app.route("/api/find_matches_for_patient/<patient_id>")
@login_required
def api_find_matches_for_patient(patient_id):
    """API endpoint to get slots matching a specific patient's requirements."""
    user_provider_manager, user_waitlist_manager, user_slot_manager = get_user_managers(
        current_user.username
    )

    patient = user_waitlist_manager.get_patient(patient_id)

    if not patient:
        return jsonify({"error": "Patient not found"}), 404
    if patient.get("status", "waiting") != "waiting":
        return jsonify({"error": "Patient is not currently waiting", "status": patient.get("status")}), 400 # Use 400 Bad Request

    # Get all available slots (status 'available')
    all_slots = user_slot_manager.get_all_slots()
    available_slots = [
        slot for slot in all_slots if slot.get("status", "available") == "available"
    ]
    logging.debug(f"Found {len(available_slots)} available slots for patient {patient_id}")


    # Filter slots based on patient requirements (Logic copied from api_matching_slots)
    matching_slots = []
    patient_duration = int(patient.get("duration", 0))
    patient_provider_pref = patient.get("provider", "no preference").lower()
    patient_availability = patient.get("availability", {})
    patient_availability_mode = patient.get("availability_mode", "available")


    for slot in available_slots:
        # Check duration
        slot_duration = int(slot.get("duration", 0))
        if patient_duration > slot_duration:
            logging.debug(f"Slot {slot.get('id')} rejected: Duration mismatch ({slot_duration} < {patient_duration})")
            continue

        # Check provider
        slot_provider = slot.get("provider", "").lower()
        if patient_provider_pref != "no preference" and patient_provider_pref != slot_provider:
            logging.debug(f"Slot {slot.get('id')} rejected: Provider mismatch ('{slot_provider}' != '{patient_provider_pref}')")
            continue

        # Check availability
        slot_date_str = slot.get("slot_date")
        slot_period = slot.get("slot_period", "").upper() # AM/PM

        slot_date = None
        if isinstance(slot_date_str, str):
            try:
                slot_date = datetime.strptime(slot_date_str, "%Y-%m-%d")
            except ValueError:
                 logging.warning(f"Could not parse slot date '{slot_date_str}' for slot {slot.get('id')}")
                 continue # Skip if date is invalid
        elif isinstance(slot_date_str, datetime):
             slot_date = slot_date_str
        else:
             logging.warning(f"Invalid slot date type '{type(slot_date_str)}' for slot {slot.get('id')}")
             continue # Skip if date is invalid type


        if patient_availability: # Only check if patient specified preferences
            slot_weekday = slot_date.strftime("%A") # Full day name e.g. Monday
            day_periods = patient_availability.get(slot_weekday, []) # Patient's pref for this day

            is_available_on_day_period = slot_period in day_periods

            if patient_availability_mode == "available":
                # Patient must be explicitly available
                if not day_periods or not is_available_on_day_period:
                    logging.debug(f"Slot {slot.get('id')} rejected: Availability mismatch (mode: available, day: {slot_weekday}, period: {slot_period}, prefs: {day_periods})")
                    continue
            else: # patient_availability_mode == "unavailable"
                # Patient must NOT be explicitly unavailable
                if day_periods and is_available_on_day_period:
                    logging.debug(f"Slot {slot.get('id')} rejected: Availability mismatch (mode: unavailable, day: {slot_weekday}, period: {slot_period}, prefs: {day_periods})")
                    continue

        # If all checks pass, add the slot
        logging.debug(f"Slot {slot.get('id')} matched for patient {patient_id}")
        matching_slots.append(slot)

    # Sort matching slots by date
    def sort_key(slot):
        date_str = slot.get("slot_date")
        if isinstance(date_str, str):
            try:
                return datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                return datetime.max # Put unparseable dates last
        elif isinstance(date_str, datetime):
            return date_str
        return datetime.max # Put slots with missing/invalid dates last

    matching_slots.sort(key=sort_key)

    logging.info(f"Returning {len(matching_slots)} matching slots for patient {patient_id}")
    # Return only necessary slot info for the modal
    # Convert date obj back to string for JSON if needed
    result_slots = []
    for slot in matching_slots:
        slot_data = slot.copy()
        if isinstance(slot_data.get("slot_date"), datetime):
            slot_data["slot_date"] = slot_data["slot_date"].strftime('%Y-%m-%d')
        result_slots.append(slot_data)


    return jsonify({"patient": patient, "matching_slots": result_slots})


if __name__ == "__main__":
    # create data/users folder if it doesn't exist
    if not os.path.exists("data/users"):
        os.makedirs("data/users")
    app.run(debug=True, host="0.0.0.0", port=7776)
