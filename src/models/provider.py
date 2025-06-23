from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class Provider(db.Model):
    """SQLAlchemy model for providers table."""
    
    __tablename__ = 'providers'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_initial = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'first_name': self.first_name,
            'last_initial': self.last_initial,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create model from dictionary."""
        return cls(
            id=data.get('id'),
            user_id=data.get('user_id'),
            first_name=data.get('first_name'),
            last_initial=data.get('last_initial')
        ) 