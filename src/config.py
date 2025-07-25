import os
from datetime import timedelta
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import logging

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration class."""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', os.environ.get('FLASK_SESSION_SECRET_KEY', 'dev'))
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = False  # Set to False for development
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Session Configuration
    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = True
    SESSION_FILE_THRESHOLD = 500
    SESSION_FILE_MODE = 0o600
    SESSION_USE_SIGNER = True
    
    # Encryption
    ENCRYPTION_KEY = os.environ.get("FLASK_APP_ENCRYPTION_KEY")
    
    # Stripe Configuration
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY") 
    STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID")  # For subscription price
    STRIPE_PAYMENT_LINK = os.environ.get("STRIPE_PAYMENT_LINK", "https://buy.stripe.com/6oU28qfPb06P5pygNsdby03")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")  # For webhook validation
    
    # File Storage
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # PostgreSQL Configuration
    DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")

    # Fix for Supabase: Use connection pooling port and add timeout settings
    if DATABASE_URL and "supabase.co:5432" in DATABASE_URL:
        # Replace direct port 5432 with pooling port 6543
        DATABASE_URL = DATABASE_URL.replace(":5432/", ":6543/")
        print(f"Updated DATABASE_URL to use pooling port: {DATABASE_URL}")

    if not DATABASE_URL:
        # Fallback to individual components
        DB_HOST = os.environ.get("DB_HOST", "localhost")
        DB_PORT = os.environ.get("DB_PORT", "5432")
        DB_NAME = os.environ.get("DB_NAME", "waitlyst")
        DB_USER = os.environ.get("DB_USER", "postgres")
        DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    # Database URL (PostgreSQL only)
    DATABASE_URL_FINAL = DATABASE_URL
    
    # File Storage
    DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
    USERS_DIR = os.path.join(DATA_DIR, 'users')
    SESSIONS_DIR = os.path.join(DATA_DIR, 'flask_sessions')
    DIFF_STORE_DIR = os.path.join(DATA_DIR, 'diff_store')
    
    @classmethod
    def validate_env_vars(cls):
        """Validate that required environment variables are set."""
        required_vars = []
        
        # Check Stripe configuration
        if not cls.STRIPE_SECRET_KEY:
            required_vars.append("STRIPE_SECRET_KEY")
        
        if required_vars:
            missing_vars = ", ".join(required_vars)
            logging.warning(f"Missing environment variables: {missing_vars}")
            logging.warning("Some Stripe features may not work properly.")
        
        logging.info("Environment validation completed.")
    
    @classmethod
    def setup_directories(cls):
        """Create necessary directories if they don't exist."""
        # Create necessary directories
        directories = [cls.DATA_DIR, cls.USERS_DIR, cls.SESSIONS_DIR, cls.DIFF_STORE_DIR]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        # Verify session directory is writable
        test_file = os.path.join(cls.SESSIONS_DIR, "test_write.tmp")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        
        logging.info(f"Session directory verified at: {cls.SESSIONS_DIR}")
    
    @classmethod
    def get_cipher_suite(cls):
        """Get the encryption cipher suite."""
        if not cls.ENCRYPTION_KEY:
            raise ValueError("CRITICAL: FLASK_APP_ENCRYPTION_KEY environment variable not set!")
        return Fernet(cls.ENCRYPTION_KEY.encode())
    
    @classmethod
    def setup_logging(cls):
        """Configure logging."""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ) 