from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required
from src.models.user import User
from src.database import get_supabase_client
import json
import re
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)
supabase = get_supabase_client()

@auth_bp.route("/register", methods=["GET", "POST"])
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

@auth_bp.route("/login", methods=["GET", "POST"])
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

@auth_bp.route("/logout")
@login_required
def logout():
    # Sign out from Supabase
    supabase.auth.sign_out()
    # Log out from Flask-Login
    logout_user()
    # Clear session
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for("login")) 