from src.models.user import User
from src.models.provider import db
import logging

logger = logging.getLogger(__name__)

class UserRepository:
    """Repository for user operations with SQLite database."""
    
    def get_by_id(self, user_id):
        """Get user by ID."""
        try:
            return User.query.get(user_id)
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
        return None
    
    def get_by_username(self, username):
        """Get user by username."""
        try:
            return User.query.filter_by(username=username).first()
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
        return None
    
    def get_by_email(self, email):
        """Get user by email."""
        try:
            return User.query.filter_by(email=email).first()
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {e}")
        return None
    
    def create(self, user_data):
        """Create a new user."""
        try:
            user = User.from_dict(user_data)
            db.session.add(user)
            db.session.commit()
            return user
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            db.session.rollback()
        return None
    
    def update(self, user_id, user_data):
        """Update user data."""
        try:
            user = User.query.get(user_id)
            if user:
                for key, value in user_data.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                db.session.commit()
                return user
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            db.session.rollback()
        return None
    
    def delete(self, user_id):
        """Delete user."""
        try:
            user = User.query.get(user_id)
            if user:
                db.session.delete(user)
                db.session.commit()
                return True
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            db.session.rollback()
        return False
    
    def get_all(self):
        """Get all users."""
        try:
            return User.query.all()
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
        return [] 