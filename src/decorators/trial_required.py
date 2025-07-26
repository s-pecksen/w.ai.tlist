"""
Trial Required Decorator - Enforces Stripe Verification
Ensures users have completed Stripe checkout before accessing app features.
"""

from functools import wraps
from flask import redirect, url_for, flash, session, request
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)

def trial_required(f):
    """
    Decorator that ensures user has completed Stripe checkout and has valid access.
    This is more strict than just @login_required - it verifies Stripe status.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First check if user is logged in
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        

        
        # Check trial/subscription status only
        try:
            from src.services.trial_service import trial_service
            
            # Check trial/subscription status
            trial_status = trial_service.get_trial_status(current_user)
            
            if not trial_status['has_access']:
                # Trial expired and no subscription
                logger.warning(f"Access denied for {current_user.email}: {trial_status['access_type']}")
                flash("Your free trial has expired. Please subscribe to continue using Waitlyst.", "error")
                return redirect(url_for('payments.subscribe'))
            
            # User has valid access - proceed with the function
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error in trial_required decorator for {current_user.email}: {e}")
            flash("There was an error verifying your account. Please try again.", "error")
            return redirect(url_for('auth.login'))
    
    return decorated_function 