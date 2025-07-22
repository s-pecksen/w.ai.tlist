from flask import Flask, session, request
from flask_login import LoginManager
from src.config import Config
from src.models.user import User
from src.models.provider import db, Provider
from src.models.patient import Patient
from src.models.slot import Slot
from src.routes.auth import auth_bp
from src.routes.patients import patients_bp
from src.routes.slots import slots_bp
from src.routes.providers import providers_bp
from src.routes.appointment_types import appointment_types_bp
from src.routes.main import main_bp
from src.routes.settings import settings_bp
from src.routes.payments import payments_bp
import logging

# Configure logging
Config.setup_logging()
logger = logging.getLogger(__name__)

# Validate environment variables
Config.validate_env_vars()

# Setup directories
Config.setup_directories()

# Configure Flask app
app = Flask(__name__)

# Apply configuration
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = Config.PERMANENT_SESSION_LIFETIME
app.config['SESSION_COOKIE_SECURE'] = Config.SESSION_COOKIE_SECURE
app.config['SESSION_COOKIE_HTTPONLY'] = Config.SESSION_COOKIE_HTTPONLY
app.config['SESSION_COOKIE_SAMESITE'] = Config.SESSION_COOKIE_SAMESITE

# Session configuration
app.config["SESSION_TYPE"] = Config.SESSION_TYPE
app.config["SESSION_PERMANENT"] = Config.SESSION_PERMANENT
app.config["SESSION_FILE_DIR"] = Config.SESSIONS_DIR
app.config["SESSION_FILE_THRESHOLD"] = Config.SESSION_FILE_THRESHOLD
app.config["SESSION_FILE_MODE"] = Config.SESSION_FILE_MODE
app.config["SESSION_USE_SIGNER"] = Config.SESSION_USE_SIGNER
app.config["PERSISTENT_STORAGE_PATH"] = Config.DATA_DIR
app.config["USERS_DIR"] = Config.USERS_DIR

# Database configuration - SQLite only
app.config['SQLALCHEMY_DATABASE_URI'] = Config.LOCAL_DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Add connection timeout and pool settings for PostgreSQL
if 'postgresql://' in Config.LOCAL_DATABASE_URL:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_timeout': 10,
        'pool_recycle': 300,
        'connect_args': {
            'connect_timeout': 10
        }
    }

logger.info(f"Using database: {Config.LOCAL_DATABASE_URL}")
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()
    logger.info("SQLite database tables created")
# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "error"

# Flask-Login user loader callback
@login_manager.user_loader
def load_user(user_id):
    """Load user by ID from SQLite database."""
    try:
        user = db.session.get(User, user_id)
        if user:
            logger.debug(f"Loaded user {user_id} - clinic_name: '{user.clinic_name}', user_name_for_message: '{user.user_name_for_message}'")
            return user
        else:
            logger.debug(f"User {user_id} not found in database")
    except Exception as e:
        logger.warning(f"Could not load user {user_id}. Error: {e}")
    
    return None

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(patients_bp)
app.register_blueprint(slots_bp)
app.register_blueprint(providers_bp)
app.register_blueprint(appointment_types_bp)
app.register_blueprint(main_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(payments_bp)

# Security headers
@app.before_request
def add_security_headers():
    """Add security headers to all responses."""
    pass

@app.after_request
def add_security_headers_after(response):
    """Add security headers after response is created."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

@app.after_request
def add_cors_headers(response):
    """Add CORS headers."""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# Logging middleware
@app.before_request
def log_request_info():
    """Log request information."""
    logger.info(f"Request: {request.method} {request.url}")

@app.after_request
def log_response_info(response):
    """Log response information."""
    logger.info(f"Response: {response.status_code}")
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860, debug=True) 