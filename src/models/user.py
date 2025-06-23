import json
from flask_login import UserMixin
from src.models.provider import db
from datetime import datetime
import uuid

class User(UserMixin, db.Model):
    """SQLAlchemy User model for authentication and user data."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(200), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))  # For local auth if needed
    clinic_name = db.Column(db.String(200))
    user_name_for_message = db.Column(db.String(200))
    appointment_types = db.Column(db.Text)  # JSON string
    appointment_types_data = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert user object to dictionary for storage."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "clinic_name": self.clinic_name,
            "user_name_for_message": self.user_name_for_message,
            "appointment_types": self.appointment_types,
            "appointment_types_data": self.appointment_types_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data):
        """Create user object from dictionary."""
        return cls(
            id=data.get("id"),
            username=data.get("username"),
            email=data.get("email"),
            clinic_name=data.get("clinic_name"),
            user_name_for_message=data.get("user_name_for_message"),
            appointment_types=data.get("appointment_types"),
            appointment_types_data=data.get("appointment_types_data")
        ) 