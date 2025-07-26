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
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        clinic_name = request.form.get("clinic_name", "").strip()
        user_name_for_message = request.form.get("user_name", "").strip()

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

        # Check if user already exists
        existing_user = user_repo.get_by_email(email)
        if existing_user:
            flash("An account with this email already exists.", "error")
            return render_template("register.html")

        # --- Parse JSON data ---
        try:
            appointment_types_data = json.loads(appointment_types_json)
            providers_data = json.loads(providers_json)
            appointment_types_list = [item.get('appointment_type', '') for item in appointment_types_data if item.get('appointment_type')]
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
            
            user = user_repo.create(user_data)
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
                        if not result:
                            logger.warning(f"Failed to create provider: {provider_data.get('first_name')}")
                
                logger.info(f"Processed {len(providers_data)} providers from registration form")
                
        except Exception as e:
            logger.error(f"Failed to create user {email}. Error: {e}", exc_info=True)
            flash("Error creating user. Please try again.", "error")
            return render_template("register.html")

        # --- Create Stripe Customer with Email Verification ---
        logger.info(f"User {email} registered successfully, creating Stripe customer with email verification")
        
        # Create Stripe customer with email verification enabled
        customer = payment_service.create_customer_with_email_verification(email)
        if not customer:
            logger.warning(f"Failed to create Stripe customer for {email}, but continuing with registration")
        
        # Log the user in immediately
        login_user(user)
        
        # Clear any accumulated session data
        session.pop('pending_user_email', None)
        session.pop('just_registered', None)
        session.pop('login_after_checkout', None)
        
        logger.info(f"New user {email} logged in successfully and free trial started")
        flash("Welcome to Waitlyst! Your free trial has started. Please check your email to verify your account.", "success")
        return redirect(url_for("main.index"))

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

        # --- Create Stripe customer if needed (for free trial tracking) ---
        # Check if user has a Stripe customer record
        stripe_customer = payment_service.get_customer_by_email(email)
        
        if not stripe_customer:
            # Create Stripe customer for free trial tracking (no payment required)
            logger.info(f"Creating Stripe customer for {email} during login")
            customer = payment_service.create_customer_for_free_trial(email)
            if not customer:
                logger.warning(f"Failed to create Stripe customer for {email}, but allowing login")
                # Continue with login even if Stripe customer creation fails
        
        # User has Stripe customer record - now check their subscription status
        trial_status = trial_service.get_trial_status(user)
        
        if not trial_status['has_access']:
            # Trial expired and no active subscription
            logger.warning(f"Login denied for {email}: {trial_status['access_type']} - no access")
            subscribe_url = url_for('payments.subscribe')
            flash(f"Your free trial has expired. Please subscribe to continue using the service. <a href='{subscribe_url}'>Subscribe here</a>", "error")
            return render_template("login.html")

        # --- Proceed with login ---
        login_user(user, remember=remember)
        session.permanent = remember
        
        # Clear any accumulated session data
        session.pop('pending_user_email', None)
        session.pop('just_registered', None)
        session.pop('login_after_checkout', None)
        
        # Show warning if trial is ending soon and no subscription
        if trial_status['requires_payment'] and not trial_status['is_subscriber']:
            subscribe_url = url_for('payments.subscribe')
            flash(f"{trial_status['warning_message']} <a href='{subscribe_url}'>Subscribe here</a>", "warning")
        
        logger.info(f"User {email} logged in successfully - access_type: {trial_status['access_type']}")
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

 