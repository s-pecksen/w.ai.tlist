from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from typing import Dict, Any
import os
from sqlalchemy import event, create_engine
from sqlalchemy.engine import Engine
import logging
from cryptography.fernet import Fernet

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy
db = SQLAlchemy()

# Configure encryption
def configure_encryption(app):
    """Configure encryption for the database."""
    try:
        # Get encryption key from environment
        encryption_key = os.environ.get("FLASK_APP_ENCRYPTION_KEY")
        if not encryption_key:
            raise ValueError("FLASK_APP_ENCRYPTION_KEY environment variable not set!")
        
        # Create cipher suite
        cipher_suite = Fernet(encryption_key.encode())
        
        # Set up encryption for sensitive fields
        @event.listens_for(Engine, "connect")
        def set_encryption(dbapi_connection, connection_record):
            # Enable foreign keys
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.close()
            
        logging.info("Database encryption configuration completed successfully")
        return cipher_suite
    except Exception as e:
        logging.error(f"Error configuring database encryption: {e}")
        return None

class EncryptedString(db.TypeDecorator):
    """Custom type for encrypted string fields."""
    impl = db.String
    
    def __init__(self, length=None):
        super().__init__(length)
        self.key = os.environ.get("FLASK_APP_ENCRYPTION_KEY")
        if not self.key:
            raise ValueError("FLASK_APP_ENCRYPTION_KEY environment variable not set!")
        try:
            self.cipher_suite = Fernet(self.key.encode())
        except Exception as e:
            raise ValueError(f"Invalid FLASK_APP_ENCRYPTION_KEY: {e}")
    
    def process_bind_param(self, value, dialect):
        """Encrypt the value before storing in the database."""
        if value is not None:
            return self.cipher_suite.encrypt(value.encode()).decode()
        return value
    
    def process_result_value(self, value, dialect):
        """Decrypt the value when retrieving from the database."""
        if value is not None:
            return self.cipher_suite.decrypt(value.encode()).decode()
        return value

class Provider(db.Model):
    __tablename__ = 'providers'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_initial = db.Column(db.String(1))
    user_id = db.Column(db.String(100), nullable=False)  # To separate providers by user
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': f"{self.first_name} {self.last_initial}" if self.last_initial else self.first_name,
            'first_name': self.first_name,
            'last_initial': self.last_initial
        }

class Patient(db.Model):
    __tablename__ = 'patients'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    name = db.Column(EncryptedString(100), nullable=False)
    phone = db.Column(EncryptedString(20), nullable=False)
    email = db.Column(EncryptedString(100))
    reason = db.Column(EncryptedString(500))
    urgency = db.Column(db.String(20), default='medium')
    appointment_type = db.Column(db.String(50))
    duration = db.Column(db.Integer, default=30)
    provider = db.Column(db.String(100), default='no preference')
    status = db.Column(db.String(20), default='waiting')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    wait_time = db.Column(db.String(50))
    availability = db.Column(db.Text)
    availability_mode = db.Column(db.String(20), default='available')
    proposed_slot_id = db.Column(db.String(36))
    user_id = db.Column(db.String(100), nullable=False)  # To separate patients by user
    
    def to_dict(self) -> Dict[str, Any]:
        availability = {}
        if self.availability:
            try:
                availability = json.loads(self.availability)
            except json.JSONDecodeError:
                pass
                
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'reason': self.reason,
            'urgency': self.urgency,
            'appointment_type': self.appointment_type,
            'duration': self.duration,
            'provider': self.provider,
            'status': self.status,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'wait_time': self.wait_time,
            'availability': availability,
            'availability_mode': self.availability_mode,
            'proposed_slot_id': self.proposed_slot_id,
            'user_id': self.user_id
        }

class CancelledSlot(db.Model):
    __tablename__ = 'cancelled_slots'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    provider_id = db.Column(db.Integer, db.ForeignKey('providers.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    duration = db.Column(db.Integer, default=30)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='available')
    proposed_patient_id = db.Column(db.String(36))
    proposed_patient_name = db.Column(db.String(100))
    user_id = db.Column(db.String(100), nullable=False)  # To separate slots by user
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'provider_id': self.provider_id,
            'date': self.date.isoformat() if self.date else None,
            'time': self.time.isoformat() if self.time else None,
            'duration': self.duration,
            'notes': self.notes,
            'status': self.status,
            'proposed_patient_id': self.proposed_patient_id,
            'proposed_patient_name': self.proposed_patient_name,
            'user_id': self.user_id
        }

def init_db(app):
    """Initialize the database with the Flask app."""
    # Configure encryption
    cipher_suite = configure_encryption(app)
    if not cipher_suite:
        raise RuntimeError("Failed to configure database encryption")
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        logger.info("Database initialized successfully") 