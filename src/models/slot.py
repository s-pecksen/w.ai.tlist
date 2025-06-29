from src.models.provider import db
from datetime import datetime
import uuid

class Slot(db.Model):
    """SQLAlchemy model for cancelled_slots table."""
    
    __tablename__ = 'cancelled_slots'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), nullable=False)
    provider = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(10), nullable=False)  # e.g., "09:00"
    end_time = db.Column(db.String(10), nullable=False)    # e.g., "10:00"
    duration = db.Column(db.Integer, nullable=False)       # minutes
    status = db.Column(db.String(50), default='available')
    proposed_patient_id = db.Column(db.String(36))
    proposed_patient_name = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'provider': self.provider,
            'date': self.date.isoformat() if self.date else None,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'status': self.status,
            'proposed_patient_id': self.proposed_patient_id,
            'proposed_patient_name': self.proposed_patient_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'notes': self.notes,
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create model from dictionary."""
        return cls(
            id=data.get('id'),
            user_id=data.get('user_id'),
            provider=data.get('provider'),
            date=datetime.fromisoformat(data['date']) if data.get('date') else None,
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            duration=data.get('duration'),
            status=data.get('status'),
            proposed_patient_id=data.get('proposed_patient_id'),
            proposed_patient_name=data.get('proposed_patient_name'),
            notes=data.get('notes')
        ) 