from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from datetime import datetime, timedelta, date
from cryptography.fernet import Fernet
import os
import pandas as pd
import csv
from io import StringIO
from src.provider_manager import ProviderManager
import uuid
from src.patient_waitlist_manager import PatientWaitlistManager
import shutil
import glob
import logging
from src.cancelled_slot_manager import CancelledSlotManager
import json  # Needed for handling availability JSON in CSV upload
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)

# from werkzeug.security import generate_password_hash, check_password_hash
import hashlib

app = Flask(__name__)
app.secret_key = os.urandom(24)


# Make sure to add this for flash messages to work
app.config["SESSION_TYPE"] = "filesystem"

# Define paths
backup_dir = "waitlist_backups"
cancelled_slots_backup_dir = "cancelled_slots_backups"
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


# --- Flask App Initialization ---
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Keep existing secret key

# --- Login Manager Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = (
    "login"  # Redirect user to /login if they access a protected page
)


# --- User Class ---
class User(UserMixin):
    def __init__(
        self,
        user_id,
        username,
        password_hash,
        clinic_name=None,
        user_name_for_message=None,
    ):
        self.id = user_id
        self.username = username
        self.password_hash = password_hash
        self.clinic_name = clinic_name
        self.user_name_for_message = user_name_for_message

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
    # Since we don't have an index, we need to scan all files
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
    return get_user_by_id(user_id)


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
        # TODO: Add inputs for initial providers, appt types/durations

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
        )

        try:
            save_user(new_user)
            # TODO: Save initial providers/appt types for this user
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            logging.error(f"Error during registration: {e}", exc_info=True)
            flash("An error occurred during registration. Please try again.", "danger")
            return redirect(url_for("register"))

    return render_template("register.html")  # Need to create this template


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


# Global managers for routes that don't have current_user context yet
provider_manager = ProviderManager()
waitlist_manager = PatientWaitlistManager()
slot_manager = CancelledSlotManager()


# Function to get user-specific managers
def get_user_managers(username):
    """Get managers initialized with user-specific data paths"""
    user_dir = os.path.join(users_dir, username)
    os.makedirs(user_dir, exist_ok=True)

    user_provider_manager = ProviderManager(
        provider_file=get_user_data_path(username, "provider.csv")
    )
    user_waitlist_manager = PatientWaitlistManager(
        app_name=username,
        backup_dir=os.path.join(users_dir, username, backup_dir),
        waitlist_file=get_user_data_path(
            username, "waitlist.csv"
        ),  # Add waitlist file path
    )
    user_slot_manager = CancelledSlotManager(
        slots_file=get_user_data_path(username, "cancelled_slots.csv"),
        backup_dir=os.path.join(users_dir, username, cancelled_slots_backup_dir),
    )
    return user_provider_manager, user_waitlist_manager, user_slot_manager


# Modify Index Route (Example of protecting and using current_user)
@app.route("/", methods=["GET"])
@login_required  # Protect the main page
def index():
    logging.debug(f"Entering index route for user: {current_user.id}")
    try:
        # Get user-specific managers
        user_provider_manager, user_waitlist_manager, user_slot_manager = (
            get_user_managers(current_user.username)
        )

        # Get user-specific providers
        all_providers = user_provider_manager.get_provider_list()
        has_providers = len(all_providers) > 0

        # Get all patients for this user
        all_patients = user_waitlist_manager.get_all_patients()
        waitlist = all_patients

        # --- End TEMPORARY ---

        logging.debug(
            f"Index route: Fetched {len(waitlist)} patients for user {current_user.id}"
        )

        # Sorting logic needs refactoring based on the new data structure/wait time calculation
        # sorted_waitlist = sorted(waitlist, key=sort_key_safe)
        sorted_waitlist = waitlist  # Placeholder

        if not has_providers:  # This check should also be user-specific
            flash(
                "Please add your Provider names via settings to proceed", "warning"
            )  # TODO: Add settings page

        logging.debug("Index route: Rendering index.html with user-specific waitlist")
        return render_template(
            "index.html",
            waitlist=sorted_waitlist,
            providers=all_providers,  # Now user-specific
            has_providers=has_providers,  # Now user-specific
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


@app.route("/slots", methods=["GET"])
def slots():
    logging.debug("Entering /slots route")
    try:
        all_providers = provider_manager.get_provider_list()
        has_providers = len(all_providers) > 0

        # Fetch and Sort Open Slots
        current_slots = slot_manager.get_all_slots()
        # Sort by date then time (most recent first)
        current_slots.sort(
            key=lambda s: (s.get("slot_date") or date.min, s.get("slot_time") or ""),
            reverse=True,
        )
        logging.debug(f"/slots route: Fetched {len(current_slots)} open slots")

        # Retrieve eligible patients and current appointment from flash/session if redirected
        # For a clean GET request, these will be None initially
        eligible_patients = None  # No matches shown on initial load
        current_appointment = None  # No specific slot context on initial load

        return render_template(
            "slots.html",
            providers=all_providers,
            has_providers=has_providers,
            cancelled_appointments=current_slots,
            eligible_patients=eligible_patients,
            current_appointment=current_appointment,
        )
    except Exception as e:
        logging.error(f"Exception in /slots route: {e}", exc_info=True)
        flash("An error occurred while loading the open slots page.", "danger")
        # Redirect to index on error, or show an error page? Redirecting for now.
        return redirect(url_for("index"))


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
def remove_patient(patient_id):
    if waitlist_manager.remove_patient(patient_id):
        flash("Patient removed successfully.", "success")
    else:
        flash("Failed to remove patient.", "danger")
    # Redirect back to the index page, focusing on the waitlist table
    return redirect(url_for("index") + "#waitlist-table")  # Added fragment


# --- Add New Route for Manual Backup ---
@app.route("/save_backup", methods=["POST"])
def save_backup():
    """Manually saves a timestamped backup of the waitlist."""
    try:
        waitlist_manager.save_backup()
        flash("Waitlist backup saved successfully.", "success")
    except Exception as e:
        print(f"Error during manual backup: {str(e)}")
        flash(f"Error saving backup: {str(e)}", "danger")
    # Redirect back to index, maybe near the top or an actions area
    return redirect(
        url_for("index") + "#page-top"
    )  # Added fragment (use a relevant ID)


# --- End New Route ---


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
def list_providers():
    providers = provider_manager.get_provider_list()
    return render_template("providers.html", providers=providers)


@app.route("/providers/add", methods=["POST"])
def add_provider():
    first_name = request.form.get("first_name")
    last_initial = request.form.get("last_initial")

    if first_name:
        # Call add_provider without is_active
        success = provider_manager.add_provider(first_name, last_initial)
        if success:
            flash("Provider added successfully", "success")
        else:
            flash("Provider already exists", "danger")
    else:
        flash("First name is required", "danger")

    # Redirect back to providers list
    return redirect(url_for("list_providers") + "#provider-list")  # Added fragment


@app.route("/providers/remove", methods=["POST"])
def remove_provider():
    first_name = request.form.get("first_name")
    last_initial = request.form.get("last_initial")

    if provider_manager.remove_provider(first_name, last_initial):
        flash("Provider removed successfully")
    else:
        flash("Provider not found")

    # Redirect back to providers list
    return redirect(url_for("list_providers") + "#provider-list")  # Added fragment


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=7776)
