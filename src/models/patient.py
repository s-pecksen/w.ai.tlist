from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class Patient(db.Model):
    """SQLAlchemy model for patients table."""
    
    __tablename__ = 'patients'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(200))
    appointment_type = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(10), nullable=False)
    provider = db.Column(db.String(100))
    urgency = db.Column(db.String(20), default='medium')
    status = db.Column(db.String(50), default='waiting')
    availability = db.Column(db.Text)  # JSON string
    availability_mode = db.Column(db.String(20), default='available')
    reason = db.Column(db.Text)
    proposed_slot_id = db.Column(db.String(36))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'appointment_type': self.appointment_type,
            'duration': self.duration,
            'provider': self.provider,
            'urgency': self.urgency,
            'status': self.status,
            'availability': self.availability,
            'availability_mode': self.availability_mode,
            'reason': self.reason,
            'proposed_slot_id': self.proposed_slot_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create model from dictionary."""
        return cls(
            id=data.get('id'),
            user_id=data.get('user_id'),
            name=data.get('name'),
            phone=data.get('phone'),
            email=data.get('email'),
            appointment_type=data.get('appointment_type'),
            duration=data.get('duration'),
            provider=data.get('provider'),
            urgency=data.get('urgency'),
            status=data.get('status'),
            availability=data.get('availability'),
            availability_mode=data.get('availability_mode'),
            reason=data.get('reason'),
            proposed_slot_id=data.get('proposed_slot_id')
        ) 