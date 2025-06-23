import json
from flask_login import UserMixin

class User(UserMixin):
    """User model for authentication and user data."""
    
    def __init__(
        self,
        user_id,
        username,
        clinic_name=None,
        user_name_for_message=None,
        appointment_types=None,
        appointment_types_data=None,
    ):
        self.id = user_id
        self.username = username
        self.clinic_name = clinic_name or ""
        self.user_name_for_message = user_name_for_message or ""
        self.appointment_types = appointment_types or []
        self.appointment_types_data = appointment_types_data or []

    def to_dict(self):
        """Convert user object to dictionary for storage."""
        return {
            "id": self.id,
            "username": self.username,
            "clinic_name": self.clinic_name,
            "user_name_for_message": self.user_name_for_message,
            "appointment_types": self.appointment_types,
            "appointment_types_data": self.appointment_types_data
        }

    @classmethod
    def from_dict(cls, data):
        """Create user object from dictionary."""
        # Parse JSON strings back to lists if needed
        appointment_types = data.get("appointment_types", [])
        appointment_types_data = data.get("appointment_types_data", [])
        
        if isinstance(appointment_types, str):
            appointment_types = json.loads(appointment_types)
        
        if isinstance(appointment_types_data, str):
            appointment_types_data = json.loads(appointment_types_data)
        
        return cls(
            user_id=data.get("id"),
            username=data.get("username"),
            clinic_name=data.get("clinic_name"),
            user_name_for_message=data.get("user_name_for_message"),
            appointment_types=appointment_types,
            appointment_types_data=appointment_types_data
        ) 