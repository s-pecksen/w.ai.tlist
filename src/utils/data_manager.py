import os
from src.config import Config
from cryptography.fernet import Fernet

class DataManager:
    """Handles encryption and decryption of the database for backup/restore."""
    def __init__(self):
        self.db_path = os.path.join(Config.PROJECT_ROOT, 'instance', 'waitlist.db')
        self.cipher = Config.get_cipher_suite()

    def export_encrypted_db(self, out_path):
        """Encrypt and export the database file to out_path."""
        with open(self.db_path, 'rb') as f:
            data = f.read()
        encrypted = self.cipher.encrypt(data)
        with open(out_path, 'wb') as f:
            f.write(encrypted)
        return out_path

    def import_encrypted_db(self, in_path):
        """Decrypt and import the database file from in_path."""
        with open(in_path, 'rb') as f:
            encrypted = f.read()
        decrypted = self.cipher.decrypt(encrypted)
        with open(self.db_path, 'wb') as f:
            f.write(decrypted)
        return self.db_path 