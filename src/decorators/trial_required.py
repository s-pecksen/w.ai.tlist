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
            flash("Please log in to access this feature.", "info")
            return redirect(url_for('auth.login'))
        
        # Check Stripe verification and trial status
        try:
            from src.services.trial_service import trial_service
            from src.services.payment_service import payment_service
            
            # Check if user has Stripe customer record
            stripe_customer = payment_service.get_customer_by_email(current_user.email)
            
            if not stripe_customer:
                # User logged in but never completed Stripe checkout
                logger.warning(f"Access denied for {current_user.email}: no Stripe verification")
                
                # Store where they were trying to go
                session['next_url'] = request.url
                session['pending_user_email'] = current_user.email
                session['login_after_checkout'] = True
                
                # Build checkout URLs
                success_url = request.url_root.rstrip('/') + url_for('payments.payment_success')
                cancel_url = request.url_root.rstrip('/') + url_for('main.index')
                
                # Create checkout session
                checkout_session = payment_service.create_checkout_session(
                    customer_email=current_user.email,
                    success_url=success_url,
                    cancel_url=cancel_url
                )
                
                if checkout_session:
                    flash("Please complete the required setup to access this feature.", "warning")
                    return redirect(checkout_session['url'])
                else:
                    # Fallback to payment link
                    payment_link = payment_service.get_payment_link_url()
                    flash("Please complete the required setup to access this feature.", "warning")
                    return redirect(payment_link)
            
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