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
import stripe
import json
import os
from src.decorators.trial_required import trial_required

# Configure logging
Config.setup_logging()
logger = logging.getLogger(__name__)

# Validate environment variables
Config.validate_env_vars()

# Setup directories
Config.setup_directories()

# Initialize Stripe with API key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")  # should be sk_test_...
if stripe.api_key:
    if stripe.api_key.startswith("sk_test_"):
        logger.info("Stripe TEST API key loaded successfully")
    elif stripe.api_key.startswith("sk_live_"):
        logger.info("Stripe LIVE API key loaded successfully")
    else:
        logger.warning("Unknown Stripe key format detected")
else:
    logger.warning("STRIPE_SECRET_KEY not found in environment variables")

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

# Database configuration - PostgreSQL only
app.config['SQLALCHEMY_DATABASE_URI'] = Config.DATABASE_URL_FINAL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# PostgreSQL connection settings
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_timeout': 10,
    'pool_recycle': 300,
    'connect_args': {
        'connect_timeout': 10
    }
}

logger.info(f"Using database: {Config.DATABASE_URL_FINAL}")
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()
    logger.info("PostgreSQL database tables created")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "error"

# Stripe Webhook Route - Direct on main app for reliability
@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    """
    Handle Stripe webhook events - Direct route for maximum reliability.
    This is where Stripe notifies us about payment events automatically!
    """
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        # Verify that this request actually came from Stripe (security!)
        if Config.STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload, sig_header, Config.STRIPE_WEBHOOK_SECRET
            )
        else:
            # For local testing without webhook secret
            event = json.loads(payload)
            logger.warning("Processing webhook without signature verification (local testing only)")
        
        logger.info(f"Stripe webhook received: {event['type']}")
        
        # Handle the specific events we care about
        if event['type'] == 'checkout.session.completed':
            session_obj = event['data']['object']
            customer_email = session_obj.get('customer_email')
            subscription_id = session_obj.get('subscription')
            logger.info(f"Payment completed for {customer_email}, subscription: {subscription_id}")
            
        elif event['type'] == 'customer.subscription.created':
            subscription = event['data']['object']
            subscription_id = subscription.get('id')
            status = subscription.get('status')
            logger.info(f"New subscription created: {subscription_id} with status: {status}")
            
        elif event['type'] == 'customer.subscription.updated':
            subscription = event['data']['object']
            subscription_id = subscription.get('id')
            status = subscription.get('status')
            logger.info(f"Subscription updated: {subscription_id} status: {status}")
            
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            subscription_id = subscription.get('id')
            logger.warning(f"Subscription cancelled: {subscription_id}")
            
        elif event['type'] == 'invoice.payment_failed':
            invoice = event['data']['object']
            customer_id = invoice.get('customer')
            subscription_id = invoice.get('subscription')
            attempt_count = invoice.get('attempt_count', 0)
            logger.warning(f"Payment failed for customer: {customer_id}, subscription: {subscription_id}, attempt: {attempt_count}")
            
        elif event['type'] == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            customer_id = invoice.get('customer')
            subscription_id = invoice.get('subscription')
            logger.info(f"Payment succeeded for customer: {customer_id}, subscription: {subscription_id}")
            
        else:
            logger.debug(f"Unhandled webhook type: {event['type']}")
        
        return 'success', 200
        
    except ValueError as e:
        logger.error(f"Invalid webhook payload: {e}")
        return 'Invalid payload', 400
        
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid webhook signature: {e}")
        return 'Invalid signature', 400
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'Webhook error', 500

# Debug routes removed - no longer needed

# Flask-Login user loader callback
@login_manager.user_loader
def load_user(user_id):
    """Load user by ID from PostgreSQL database."""
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