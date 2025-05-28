import os
import json
import logging
from .encryption_utils import save_encrypted_json, load_decrypted_json

# Configure logging
logger = logging.getLogger(__name__)

# Get the path relative to the application root
PERSISTENT_STORAGE_PATH = os.environ.get("PERSISTENT_STORAGE_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))
DIFF_STORE_PATH = os.path.join(PERSISTENT_STORAGE_PATH, "diff_store")

def ensure_diff_store_exists():
    """Ensure the diff store directory exists, but don't fail if it doesn't."""
    if not os.path.exists(PERSISTENT_STORAGE_PATH):
        logger.error(f"Persistent storage path {PERSISTENT_STORAGE_PATH} does not exist!")
        return False
        
    try:
        os.makedirs(DIFF_STORE_PATH, exist_ok=True)
        logger.info(f"Diff store directory ready at: {DIFF_STORE_PATH}")
        return True
    except PermissionError:
        logger.error(f"Permission error creating diff_store directory: {DIFF_STORE_PATH}")
        return False
    except Exception as e:
        logger.error(f"Error creating diff_store directory: {e}")
        return False

def save_to_diff_store(user_id, data):
    """Save data to the diff store using encrypted storage."""
    if not ensure_diff_store_exists():
        logger.error("Cannot save to diff store - directory not available")
        return False
        
    try:
        path = os.path.join(DIFF_STORE_PATH, f"{user_id}.json")
        save_encrypted_json(data, path)
        logger.info(f"Successfully saved diff store data for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving to diff store for user {user_id}: {e}")
        return False

def load_from_diff_store(user_id):
    """Load data from the diff store using encrypted storage."""
    if not ensure_diff_store_exists():
        logger.error("Cannot load from diff store - directory not available")
        return None
        
    try:
        path = os.path.join(DIFF_STORE_PATH, f"{user_id}.json")
        data = load_decrypted_json(path)
        if data is not None:
            logger.info(f"Successfully loaded diff store data for user {user_id}")
        return data
    except Exception as e:
        logger.error(f"Error loading from diff store for user {user_id}: {e}")
        return None
