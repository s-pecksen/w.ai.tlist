from datetime import datetime
import json
import logging
from cryptography.fernet import Fernet
import os
from supabase import create_client
from typing import List, Dict, Any, Optional
import uuid
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

supabase = create_client(supabase_url, supabase_key)

# Configure encryption
def configure_encryption():
    """Configure encryption for the database."""
    try:
        encryption_key = os.environ.get("FLASK_APP_ENCRYPTION_KEY")
        if not encryption_key:
            raise ValueError("FLASK_APP_ENCRYPTION_KEY environment variable not set!")
        
        cipher_suite = Fernet(encryption_key.encode())
        logger.info("Database encryption configuration completed successfully")
        return cipher_suite
    except Exception as e:
        logger.error(f"Error configuring database encryption: {e}")
        return None

def encrypt_value(value: str, cipher_suite: Fernet) -> str:
    """Encrypt a value using the cipher suite."""
    if value is not None:
        return cipher_suite.encrypt(str(value).encode()).decode()
    return value

def decrypt_value(value: str, cipher_suite: Fernet) -> str:
    """Decrypt a value using the cipher suite."""
    if value is not None:
        return cipher_suite.decrypt(value.encode()).decode()
    return value

def init_db(app):
    """Initialize the database with the Flask app."""
    # Configure encryption
    cipher_suite = configure_encryption()
    if not cipher_suite:
        raise RuntimeError("Failed to configure database encryption")
    
    # Store cipher_suite in app context for later use
    app.cipher_suite = cipher_suite
    
    # Create tables if they don't exist
    try:
        # Test if providers table exists
        supabase.table('providers').select('*').limit(1).execute()
    except Exception as e:
        if 'does not exist' in str(e):
            try:
                # Create providers table
                supabase.table('providers').insert({
                    'first_name': 'test',
                    'user_id': 'test'
                }).execute()
                # Delete the test record
                supabase.table('providers').delete().eq('first_name', 'test').execute()
                
                # Create patients table
                supabase.table('patients').insert({
                    'name': 'test',
                    'phone': 'test',
                    'user_id': 'test'
                }).execute()
                # Delete the test record
                supabase.table('patients').delete().eq('name', 'test').execute()
                
                # Create cancelled_slots table
                supabase.table('cancelled_slots').insert({
                    'provider_id': 1,
                    'date': '2024-01-01',
                    'time': '09:00',
                    'user_id': 'test'
                }).execute()
                # Delete the test record
                supabase.table('cancelled_slots').delete().eq('date', '2024-01-01').execute()
                
                logger.info("Database tables initialized successfully")
            except Exception as create_error:
                logger.error(f"Error creating database tables: {create_error}")
                raise
        else:
            logger.error(f"Error checking database tables: {e}")
            raise

class DatabaseManager:
    """Unified database manager for all database operations."""
    
    def __init__(self, user_id: str, cipher_suite: Fernet):
        self.user_id = user_id
        self.cipher_suite = cipher_suite
    
    # Provider operations
    def get_providers(self) -> List[Dict[str, Any]]:
        """Get all providers for the current user."""
        response = supabase.table('providers').select('*').eq('user_id', self.user_id).execute()
        return response.data
    
    def add_provider(self, first_name: str, last_initial: Optional[str] = None) -> bool:
        """Add a new provider."""
        try:
            data = {
                'first_name': first_name,
                'last_initial': last_initial,
                'user_id': self.user_id
            }
            response = supabase.table('providers').insert(data).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error adding provider: {e}")
            return False
    
    def remove_provider(self, provider_id: int) -> bool:
        """Remove a provider."""
        try:
            response = supabase.table('providers').delete().eq('id', provider_id).eq('user_id', self.user_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error removing provider: {e}")
            return False
    
    # Patient operations
    def get_patients(self) -> List[Dict[str, Any]]:
        """Get all patients for the current user."""
        response = supabase.table('patients').select('*').eq('user_id', self.user_id).execute()
        patients = response.data
        for patient in patients:
            avail = patient.get('availability')
            if isinstance(avail, str):
                try:
                    patient['availability'] = json.loads(avail)
                except Exception:
                    patient['availability'] = {}
        return patients
    
    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific patient by ID."""
        response = supabase.table('patients').select('*').eq('id', patient_id).eq('user_id', self.user_id).execute()
        return response.data[0] if response.data else None
    
    def add_patient(
        self,
        name: str,
        phone: str,
        email: str = "",
        reason: str = "",
        urgency: str = "medium",
        appointment_type: str = "",
        duration: int = 30,
        provider: str = "no preference",
        availability: Optional[Dict] = None,
        availability_mode: str = "available"
    ) -> bool:
        """Add a new patient to the waitlist."""
        try:
            data = {
                'name': name,
                'phone': phone,
                'email': email,
                'reason': reason,
                'urgency': urgency,
                'appointment_type': appointment_type,
                'duration': duration,
                'provider': provider,
                'availability': json.dumps(availability) if availability else None,
                'availability_mode': availability_mode,
                'user_id': self.user_id
            }
            response = supabase.table('patients').insert(data).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error adding patient: {e}")
            return False
    
    def update_patient(
        self,
        patient_id: str,
        **updates
    ) -> bool:
        """Update a patient's information."""
        try:
            response = supabase.table('patients').update(updates).eq('id', patient_id).eq('user_id', self.user_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error updating patient: {e}")
            return False
    
    def remove_patient(self, patient_id: str) -> bool:
        """Remove a patient from the waitlist."""
        try:
            response = supabase.table('patients').delete().eq('id', patient_id).eq('user_id', self.user_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error removing patient: {e}")
            return False
    
    # Cancelled slot operations
    def get_cancelled_slots(self) -> List[Dict[str, Any]]:
        """Get all cancelled slots for the current user."""
        response = supabase.table('cancelled_slots').select('*').eq('user_id', self.user_id).execute()
        slots = response.data
        return slots
    
    def add_cancelled_slot(
        self,
        provider_id: int,
        date: str,
        time: str,
        duration: int = 30,
        notes: str = ""
    ) -> bool:
        """Add a new cancelled appointment slot."""
        try:
            data = {
                'provider_id': provider_id,
                'date': date,
                'time': time,
                'duration': duration,
                'notes': notes,
                'user_id': self.user_id
            }
            response = supabase.table('cancelled_slots').insert(data).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error adding cancelled slot: {e}")
            return False
    
    def update_cancelled_slot(
        self,
        slot_id: str,
        **updates
    ) -> bool:
        """Update a cancelled slot."""
        try:
            logging.info(f"DatabaseManager: Updating slot {slot_id} with updates: {updates}")
            
            # Convert provider to provider_id if present
            if 'provider' in updates:
                updates['provider_id'] = updates.pop('provider')
            
            # Validate required fields
            required_fields = ['provider_id', 'date', 'time', 'duration']
            missing_fields = [field for field in required_fields if field not in updates]
            if missing_fields:
                logging.error(f"Missing required fields for slot update: {missing_fields}")
                return False
                
            # Ensure time is in correct format
            if 'time' in updates:
                try:
                    time_obj = datetime.strptime(updates['time'], "%H:%M").time()
                    updates['time'] = time_obj.strftime("%H:%M")
                except ValueError as e:
                    logging.error(f"Invalid time format in database update: {updates['time']}, error: {str(e)}")
                    return False
            
            response = supabase.table('cancelled_slots').update(updates).eq('id', slot_id).eq('user_id', self.user_id).execute()
            success = bool(response.data)
            if success:
                logging.info(f"Successfully updated slot {slot_id} in database")
            else:
                logging.error(f"No data returned from database update for slot {slot_id}")
            return success
        except Exception as e:
            logging.error(f"Error updating cancelled slot {slot_id}: {str(e)}", exc_info=True)
            return False
    
    def remove_cancelled_slot(self, slot_id: str) -> bool:
        """Remove a cancelled slot."""
        try:
            response = supabase.table('cancelled_slots').delete().eq('id', slot_id).eq('user_id', self.user_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error removing cancelled slot: {e}")
            return False

    def mark_slot_as_pending(self, slot_id: str, patient_id: str, patient_name: str = "Unknown") -> bool:
        """Mark a slot as pending for a specific patient."""
        try:
            updates = {
                'status': 'pending',
                'proposed_patient_id': patient_id,
                'proposed_patient_name': patient_name
            }
            response = supabase.table('cancelled_slots').update(updates).eq('id', slot_id).eq('user_id', self.user_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error marking slot as pending: {e}")
            return False

    def cancel_slot_proposal(self, slot_id: str) -> bool:
        """Cancel a pending slot proposal."""
        try:
            updates = {
                'status': 'available',
                'proposed_patient_id': None,
                'proposed_patient_name': None
            }
            response = supabase.table('cancelled_slots').update(updates).eq('id', slot_id).eq('user_id', self.user_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error cancelling slot proposal: {e}")
            return False

    def mark_patient_as_pending(self, patient_id: str, slot_id: str) -> bool:
        """Mark a patient as pending for a specific slot."""
        try:
            updates = {
                'status': 'pending',
                'proposed_slot_id': slot_id
            }
            response = supabase.table('patients').update(updates).eq('id', patient_id).eq('user_id', self.user_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error marking patient as pending: {e}")
            return False

    def cancel_patient_proposal(self, patient_id: str) -> bool:
        """Cancel a pending patient proposal."""
        try:
            updates = {
                'status': 'waiting',
                'proposed_slot_id': None
            }
            response = supabase.table('patients').update(updates).eq('id', patient_id).eq('user_id', self.user_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error cancelling patient proposal: {e}")
            return False 