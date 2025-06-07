import os
import logging
import shutil
from datetime import datetime
import json
from src.database import db, Provider, Patient, CancelledSlot
from src.encryption_utils import load_decrypted_csv
from flask import Flask
from dotenv import load_dotenv
from app import create_app

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_persistent_storage_path():
    """Get the path to the persistent storage directory."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    storage_dir = os.path.join(base_dir, "persistent_storage")
    os.makedirs(storage_dir, exist_ok=True)
    return storage_dir

def create_app():
    """Create a Flask app for database operations."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{os.path.join(get_persistent_storage_path(), "app.db")}'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def migrate_database_file():
    """Move the SQLite database file to persistent storage."""
    storage_dir = get_persistent_storage_path()
    db_path = os.path.join(storage_dir, "app.db")
    
    # If database already exists in persistent storage, skip migration
    if os.path.exists(db_path):
        logger.info("Database already exists in persistent storage")
        return db_path
    
    # Create new database in persistent storage
    logger.info("Creating new database in persistent storage")
    return db_path

def migrate_user_data():
    """Migrate data from CSV files to the database."""
    app = create_app()
    
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Migrate providers
        providers_file = os.path.join("data", "providers.csv")
        if os.path.exists(providers_file):
            logger.info("Migrating providers...")
            with open(providers_file, 'r') as f:
                for line in f:
                    name = line.strip()
                    if name:
                        provider = Provider(name=name)
                        db.session.add(provider)
            db.session.commit()
            logger.info("Providers migration complete")
        
        # Migrate patients
        patients_file = os.path.join("data", "patients.csv")
        if os.path.exists(patients_file):
            logger.info("Migrating patients...")
            with open(patients_file, 'r') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) >= 4:
                        name, phone, email, reason = parts[:4]
                        patient = Patient(
                            name=name,
                            phone=phone,
                            email=email,
                            reason=reason
                        )
                        db.session.add(patient)
            db.session.commit()
            logger.info("Patients migration complete")
        
        # Migrate cancelled slots
        cancelled_file = os.path.join("data", "cancelled_slots.csv")
        if os.path.exists(cancelled_file):
            logger.info("Migrating cancelled slots...")
            with open(cancelled_file, 'r') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) >= 3:
                        provider_name, date_str, time_str = parts[:3]
                        try:
                            slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                            slot_time = datetime.strptime(time_str, '%H:%M').time()
                            provider = Provider.query.filter_by(name=provider_name).first()
                            if provider:
                                slot = CancelledSlot(
                                    provider_id=provider.id,
                                    date=slot_date,
                                    time=slot_time
                                )
                                db.session.add(slot)
                        except ValueError as e:
                            logger.error(f"Error parsing date/time: {e}")
            db.session.commit()
            logger.info("Cancelled slots migration complete")

def main():
    """Main migration function."""
    try:
        # Check for encryption key
        if not os.environ.get("FLASK_APP_ENCRYPTION_KEY"):
            raise ValueError("FLASK_APP_ENCRYPTION_KEY environment variable not set")
        
        # Migrate database file
        db_path = migrate_database_file()
        logger.info(f"Database file migrated to: {db_path}")
        
        # Migrate user data
        migrate_user_data()
        logger.info("Data migration complete")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    main() 