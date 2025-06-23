from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required
from src.models.user import User
from src.repositories.user_repository import UserRepository
from werkzeug.security import generate_password_hash, check_password_hash
import json
import re
import logging
import uuid

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)
user_repo = UserRepository()

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

        # Check if user already exists
        existing_user = user_repo.get_by_email(email)
        if existing_user:
            flash("An account with this email already exists.", "error")
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
                raise Exception("Failed to create user in database.")

            logger.info(f"Successfully created user with ID: {user.id}")
            
            # TODO: Insert initial providers from the registration form
            # This would require the ProviderRepository to be updated similarly
            
        except Exception as e:
            logger.error(f"Failed to create user {email}. Error: {e}", exc_info=True)
            flash("Error creating user. Please try again.", "error")
            return render_template("register.html")

        # --- Login User and Redirect ---
        login_user(user)
        logger.info(f"User {email} registered and logged in successfully")
        flash("Registration successful!", "success")
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
        if not check_password_hash(user.password_hash, password):
            flash("Invalid email or password", "error")
            return render_template("login.html")

        # --- Proceed with login ---
        login_user(user, remember=remember)
        session.permanent = remember
        
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