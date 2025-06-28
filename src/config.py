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
    
    # File Storage
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Database Configuration - SQLite Only
    LOCAL_DATABASE_URL = os.environ.get("LOCAL_DATABASE_URL", f"sqlite:///{os.path.join(PROJECT_ROOT, 'instance', 'waitlist.db')}")
    
    # File Storage
    DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
    USERS_DIR = os.path.join(DATA_DIR, 'users')
    SESSIONS_DIR = os.path.join(DATA_DIR, 'flask_sessions')
    DIFF_STORE_DIR = os.path.join(DATA_DIR, 'diff_store')
    
    @classmethod
    def validate_env_vars(cls):
        """Validate that required environment variables are set."""
        # No Supabase validation needed - SQLite only
        pass
    
    @classmethod
    def setup_directories(cls):
        """Create necessary directories if they don't exist."""
        # Add instance directory for SQLite database
        instance_dir = os.path.join(cls.PROJECT_ROOT, 'instance')
        directories = [cls.DATA_DIR, cls.USERS_DIR, cls.SESSIONS_DIR, cls.DIFF_STORE_DIR, instance_dir]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        # Verify session directory is writable
        test_file = os.path.join(cls.SESSIONS_DIR, "test_write.tmp")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        
        logging.info(f"Session directory verified at: {cls.SESSIONS_DIR}")
        logging.info(f"Instance directory created at: {instance_dir}")
    
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