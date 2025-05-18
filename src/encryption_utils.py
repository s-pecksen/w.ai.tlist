import os
import json
import csv
import io
import logging
from cryptography.fernet import Fernet

# Configure logging
logger = logging.getLogger(__name__)

# Get encryption key from environment
ENCRYPTION_KEY = os.environ.get("FLASK_APP_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    logger.error("FLASK_APP_ENCRYPTION_KEY environment variable not set!")
    raise ValueError("FLASK_APP_ENCRYPTION_KEY environment variable not set!")

try:
    cipher_suite = Fernet(ENCRYPTION_KEY.encode())
except Exception as e:
    logger.error(f"Invalid FLASK_APP_ENCRYPTION_KEY: {e}")
    raise ValueError(f"Invalid FLASK_APP_ENCRYPTION_KEY: {e}")

def encrypt_data(data_bytes):
    """Encrypts bytes using the global cipher_suite."""
    return cipher_suite.encrypt(data_bytes)

def decrypt_data(encrypted_data_bytes):
    """Decrypts bytes using the global cipher_suite. Returns original bytes."""
    return cipher_suite.decrypt(encrypted_data_bytes)

def save_encrypted_json(data_dict, file_path):
    """Converts dict to JSON string, encrypts, and writes to file."""
    try:
        json_string = json.dumps(data_dict, indent=4)
        data_bytes = json_string.encode('utf-8')
        encrypted_bytes = encrypt_data(data_bytes)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, "wb") as f:
            f.write(encrypted_bytes)
        logger.info(f"Successfully saved encrypted data to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving encrypted data to {file_path}: {e}")
        return False

def load_decrypted_json(file_path):
    """Reads encrypted file, decrypts, and loads JSON into dict."""
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        logger.warning(f"File not found or empty: {file_path}")
        return None
        
    try:
        with open(file_path, "rb") as f:
            encrypted_bytes = f.read()
        decrypted_bytes = decrypt_data(encrypted_bytes)
        json_string = decrypted_bytes.decode('utf-8')
        data = json.loads(json_string)
        logger.info(f"Successfully loaded encrypted data from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Error loading encrypted data from {file_path}: {e}")
        return None

def save_encrypted_csv(list_of_dicts, file_path, fieldnames):
    """Converts list of dicts to CSV string, encrypts, and writes to file."""
    string_io = io.StringIO()
    writer = csv.DictWriter(string_io, fieldnames=fieldnames)
    writer.writeheader()
    if list_of_dicts: # Ensure writerows is not called with None or empty if that's an issue for your csv lib version
        writer.writerows(list_of_dicts)
    csv_string = string_io.getvalue()
    
    data_bytes = csv_string.encode('utf-8')
    encrypted_bytes = encrypt_data(data_bytes)
    with open(file_path, "wb") as f: # Write in binary mode
        f.write(encrypted_bytes)

def load_decrypted_csv(file_path, fieldnames_for_empty_file_check=None):
    """Reads encrypted file, decrypts, and loads CSV into list of dicts."""
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        logging.info(f"CSV file not found or empty: {file_path}. Returning empty list.")
        # If an empty file should still have headers upon first creation (unencrypted), this part might need adjustment
        # For now, if file is empty, assume no data.
        return []
    try:
        with open(file_path, "rb") as f: # Read in binary mode
            encrypted_bytes = f.read()
        
        decrypted_bytes = decrypt_data(encrypted_bytes)
        csv_string = decrypted_bytes.decode('utf-8')
        
        # Handle cases where the decrypted string might be empty or just whitespace
        if not csv_string.strip():
            logging.info(f"Decrypted CSV content is empty for {file_path}. Returning empty list.")
            return []
            
        string_io = io.StringIO(csv_string)
        reader = csv.DictReader(string_io)
        # Ensure fieldnames are present, important for DictReader
        if not reader.fieldnames and fieldnames_for_empty_file_check:
             logging.warning(f"Decrypted CSV for {file_path} has no header. Using provided fieldnames. This might indicate an issue if data was expected.")
             # This is a tricky case. If the file was truly empty and encrypted, it would decrypt to empty.
             # If it had headers, it should have them. If you expect headers even if empty data,
             # the save_encrypted_csv should ensure headers are always written.
             # For now, we will rely on DictReader to infer or fail if no headers and no data.
        
        return list(reader)
    except Exception as e:
        logging.error(f"Failed to load or decrypt CSV from {file_path}: {e}", exc_info=True)
        # Depending on severity, you might want to raise an error or return a default
        return [] # Return empty list on error
