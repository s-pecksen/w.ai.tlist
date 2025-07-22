from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required
from src.models.user import User
from src.repositories.user_repository import UserRepository
from src.repositories.provider_repository import ProviderRepository
from werkzeug.security import generate_password_hash, check_password_hash
from src.utils.stripe_checker import has_active_subscription
import json
import re
import logging
import uuid
from datetime import datetime, timedelta
from src.services.trial_service import trial_service
from src.services.payment_service import payment_service

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)
user_repo = UserRepository()
provider_repo = ProviderRepository()

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    logger.debug("Entered /register route")
    if request.method == "POST":
        logger.debug("POST request received on /register")
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        clinic_name = request.form.get("clinic_name", "").strip()
        user_name_for_message = request.form.get("user_name", "").strip()

        logger.debug(f"Form data: email={email}, clinic_name={clinic_name}, user_name_for_message={user_name_for_message}")

        # Get JSON data from hidden fields
        appointment_types_json = request.form.get("appointment_types_json", "[]")
        providers_json = request.form.get("providers_json", "[]")
        logger.debug(f"appointment_types_json={appointment_types_json}, providers_json={providers_json}")
        
        logger.info(f"Registration attempt for email: {email}")

        # --- Input Validation ---
        if not email or not password:
            logger.debug("Missing email or password")
            flash("Email and password are required", "error")
            return render_template("register.html")
        
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            logger.debug("Invalid email format")
            flash("Please enter a valid email address", "error")
            return render_template("register.html")

        # Check if user already exists
        existing_user = user_repo.get_by_email(email)
        logger.debug(f"Existing user: {existing_user}")
        if existing_user:
            logger.debug("User already exists")
            flash("An account with this email already exists.", "error")
            return render_template("register.html")

        # --- Parse JSON data ---
        try:
            appointment_types_data = json.loads(appointment_types_json)
            providers_data = json.loads(providers_json)
            appointment_types_list = [item.get('appointment_type', '') for item in appointment_types_data if item.get('appointment_type')]
            logger.debug(f"Parsed appointment_types_data: {appointment_types_data}")
            logger.debug(f"Parsed providers_data: {providers_data}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            flash("There was an error processing the form data.", "error")
            return render_template("register.html")

        # --- Create User in Local Database ---
        try:
            user_data = {
                "id": str(uuid.uuid4()),
                "username": email,
                "email": email,
                "password_hash": generate_password_hash(password),
                "clinic_name": clinic_name,
                "user_name_for_message": user_name_for_message,
                "appointment_types": json.dumps(appointment_types_list),
                "appointment_types_data": json.dumps(appointment_types_data)
            }
            logger.debug(f"User data to create: {user_data}")
            
            user = user_repo.create(user_data)
            logger.debug(f"User created: {user}")
            logger.debug(f"Created user clinic_name: '{user.clinic_name if user else 'None'}'")
            logger.debug(f"Created user user_name_for_message: '{user.user_name_for_message if user else 'None'}'")
            if not user:
                logger.error("Failed to create user in database.")
                raise Exception("Failed to create user in database.")

            logger.info(f"Successfully created user with ID: {user.id}")
            
            # Insert initial providers from the registration form
            if providers_data:
                for provider_data in providers_data:
                    if provider_data.get("first_name"):
                        provider_to_insert = {
                            "user_id": user.id,
                            "first_name": provider_data.get("first_name"),
                            "last_initial": provider_data.get("last_initial", "")
                        }
                        result = provider_repo.create(provider_to_insert)
                        if result:
                            logger.debug(f"Created provider: {provider_data.get('first_name')}")
                        else:
                            logger.warning(f"Failed to create provider: {provider_data.get('first_name')}")
                
                logger.info(f"Processed {len(providers_data)} providers from registration form")
        except Exception as e:
            logger.error(f"Failed to create user {email}. Error: {e}", exc_info=True)
            flash("Error creating user. Please try again.", "error")
            return render_template("register.html")

        # --- Login User and Redirect ---
        logger.debug("Logging in new user")
        login_user(user)
        logger.info(f"User {email} registered and logged in successfully")
        flash("Registration successful!", "success")
        return redirect(url_for("main.index"))

    logger.debug("GET request to /register, rendering form")
    return render_template("register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        remember = request.form.get("remember", False)

        if not email or not password:
            flash("Email and password are required", "error")
            return render_template("login.html")

        # Find user by email
        user = user_repo.get_by_email(email)
        if not user:
            flash("Invalid email or password", "error")
            return render_template("login.html")

        # Check password
        if not user.password_hash:
            flash("Invalid email or password", "error")
            return render_template("login.html")
            
        if not check_password_hash(user.password_hash, password):
            flash("Invalid email or password", "error")
            return render_template("login.html")

        # --- Check subscription/30-day requirement ---
        # Check if user is within 30 days of account creation
        days_since_creation = (datetime.utcnow() - user.created_at).days
        within_30_days = days_since_creation < 30
        days_left = 30 - days_since_creation
        
        # Check if user is a paying subscriber
        is_subscriber = has_active_subscription(email)
        
        logger.info(f"Login check for {email}: {days_since_creation} days since creation, within_30_days={within_30_days}, is_subscriber={is_subscriber}")
        
        # Allow login if either condition is met
        if not within_30_days and not is_subscriber:
            logger.warning(f"Login denied for {email}: trial expired and no active subscription")
            subscribe_url = url_for('payments.subscribe')
            flash(f"Your free trial has expired. Please subscribe to continue using the service. <a href='{subscribe_url}'>Subscribe here</a>", "error")
            return render_template("login.html")

        # --- Proceed with login ---
        login_user(user, remember=remember)
        session.permanent = remember
        
        # Show warning if user has less than 3 days left in trial and is not a subscriber
        if within_30_days and days_left <= 3 and not is_subscriber:
            subscribe_url = url_for('payments.subscribe')
            flash(f"Only {days_left} days left in your trial - to keep access, sign up for a subscription here: <a href='{subscribe_url}'>Subscribe here</a>", "warning")
        
        logger.info(f"User {email} logged in successfully")
        flash("Login successful!", "success")
        return redirect(url_for("main.index"))

    return render_template("login.html")

@auth_bp.route("/logout")
@login_required
def logout():
    # Log out from Flask-Login
    logout_user()
    # Clear session
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for("auth.login")) 