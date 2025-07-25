"""
Trial Service - Server-Side Trial Validation
Prevents client-side manipulation of trial periods and subscriptions.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from src.utils.stripe_checker import has_active_subscription
from src.models.user import User, db

logger = logging.getLogger(__name__)

class TrialService:
    """
    Centralized service for trial validation and subscription checking.
    All trial logic goes through this service to prevent manipulation.
    """
    
    # Trial configuration (server-side only)
    TRIAL_DAYS = 30
    WARNING_DAYS = 3  # Warn user when 3 days left
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_trial_status(self, user: User) -> Dict:
        """
        Get comprehensive trial status for a user.
        This is the single source of truth for trial validation.
        
        Returns:
            {
                'has_access': bool,           # Can user access the app?
                'access_type': str,           # 'trial', 'subscription', 'expired'
                'days_remaining': int,        # Days left in trial (0 if expired)
                'trial_expires_on': datetime, # When trial expires
                'is_subscriber': bool,        # Has active Stripe subscription
                'requires_payment': bool,     # Should show payment prompts
                'warning_message': str,       # User-facing warning message
                'created_at': datetime,       # Account creation (for reference)
            }
        """
        try:
            # Get current time (server-side, cannot be manipulated)
            now = datetime.utcnow()
            
            # Calculate trial period based on account creation
            trial_start = user.created_at
            trial_end = trial_start + timedelta(days=self.TRIAL_DAYS)
            days_since_creation = (now - trial_start).days
            days_remaining = max(0, self.TRIAL_DAYS - days_since_creation)
            
            # Check Stripe subscription status
            is_subscriber = self._check_stripe_subscription(user.email)
            
            # Determine access type and permissions - prioritize trial period over subscription status
            if days_remaining > 0:
                # User is still in free trial period (even if they have a Stripe subscription set up)
                access_type = 'trial'
                has_access = True
                requires_payment = days_remaining <= self.WARNING_DAYS
                warning_message = self._get_trial_warning_message(days_remaining)
            elif is_subscriber:
                # Trial expired but has active paid subscription
                access_type = 'subscription'
                has_access = True
                requires_payment = False
                warning_message = None
            else:
                # Trial expired and no subscription
                access_type = 'expired'
                has_access = False
                requires_payment = True
                warning_message = "Your free trial has expired. Please subscribe to continue using Waitlyst."
            
            # Log trial check for audit purposes
            self.logger.info(
                f"Trial check for {user.email}: "
                f"access_type={access_type}, days_remaining={days_remaining}, "
                f"is_subscriber={is_subscriber}, has_access={has_access}"
            )
            
            return {
                'has_access': has_access,
                'access_type': access_type,
                'days_remaining': days_remaining,
                'trial_expires_on': trial_end,
                'is_subscriber': is_subscriber,
                'requires_payment': requires_payment,
                'warning_message': warning_message,
                'created_at': trial_start,
                'days_since_creation': days_since_creation,
            }
            
        except Exception as e:
            self.logger.error(f"Error checking trial status for user {user.email}: {e}")
            # Fail secure - deny access on error
            return {
                'has_access': False,
                'access_type': 'error',
                'days_remaining': 0,
                'trial_expires_on': None,
                'is_subscriber': False,
                'requires_payment': True,
                'warning_message': 'Unable to verify account status. Please try again.',
                'created_at': user.created_at,
                'days_since_creation': 0,
            }
    
    def validate_access(self, user: User) -> Tuple[bool, Optional[str]]:
        """
        Validate if user has access to the application.
        
        Returns:
            (has_access: bool, denial_reason: str)
        """
        trial_status = self.get_trial_status(user)
        
        if trial_status['has_access']:
            return True, None
        else:
            return False, trial_status['warning_message']
    
    def _check_stripe_subscription(self, email: str) -> bool:
        """
        Check Stripe subscription status with error handling.
        """
        try:
            return has_active_subscription(email)
        except Exception as e:
            self.logger.warning(f"Stripe subscription check failed for {email}: {e}")
            # Fail gracefully - assume no subscription on Stripe error
            return False
    
    def _get_trial_warning_message(self, days_remaining: int) -> Optional[str]:
        """
        Get appropriate warning message based on days remaining.
        """
        if days_remaining <= 0:
            return "Your free trial has expired. Please subscribe to continue using Waitlyst."
        elif days_remaining <= 1:
            return f"Your trial expires tomorrow! Subscribe now to keep access to Waitlyst."
        elif days_remaining <= self.WARNING_DAYS:
            return f"Your trial expires in {days_remaining} days. Subscribe to keep access to Waitlyst."
        else:
            return None
    
    def get_subscription_url(self) -> str:
        """
        Get the Stripe subscription URL.
        Uses configurable environment variable or fallback.
        """
        from src.config import Config
        return Config.STRIPE_PAYMENT_LINK
    
    def create_trial_user(self, email: str, username: str, **kwargs) -> User:
        """
        Create a new user with trial period starting now.
        This ensures consistent trial start times.
        """
        now = datetime.utcnow()
        
        user = User(
            email=email,
            username=username,
            created_at=now,  # Explicit trial start time
            **kwargs
        )
        
        self.logger.info(f"Created new trial user {email} with trial starting {now}")
        return user
    
    def get_trial_summary_for_user(self, user: User) -> Dict:
        """
        Get user-friendly trial summary for display in UI.
        """
        status = self.get_trial_status(user)
        
        if status['access_type'] == 'subscription':
            return {
                'status_text': 'Active Subscription',
                'status_class': 'success',
                'show_upgrade': False,
                'message': 'You have an active subscription.'
            }
        elif status['access_type'] == 'trial':
            days = status['days_remaining']
            if days <= self.WARNING_DAYS:
                status_class = 'warning'
                show_upgrade = True
            else:
                status_class = 'info'
                show_upgrade = False
            
            return {
                'status_text': f'{days} days left in trial',
                'status_class': status_class,
                'show_upgrade': show_upgrade,
                'message': status['warning_message']
            }
        else:
            return {
                'status_text': 'Trial Expired',
                'status_class': 'danger',
                'show_upgrade': True,
                'message': status['warning_message']
            }


# Global instance for easy import
trial_service = TrialService() 