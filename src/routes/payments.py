"""
Payment Routes - Handle Stripe payment flow
Provides endpoints for checkout, success, cancel, and billing portal.
"""

from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from flask_login import login_required, current_user
from src.services.payment_service import payment_service
from src.services.trial_service import trial_service
import logging

logger = logging.getLogger(__name__)

payments_bp = Blueprint('payments', __name__)

# Webhook routes moved to main app.py for better reliability with Stripe deliveries

@payments_bp.route('/subscribe', methods=['GET'])
@login_required
def subscribe():
    """
    Start the subscription process - either redirect to checkout or payment link.
    """
    try:
        # Get user's trial status for context
        trial_status = trial_service.get_trial_status(current_user)
        
        # Build success and cancel URLs
        success_url = request.url_root.rstrip('/') + url_for('payments.payment_success')
        cancel_url = request.url_root.rstrip('/') + url_for('payments.payment_cancelled')
        
        # Try to create a checkout session (requires STRIPE_PRICE_ID)
        checkout_session = payment_service.create_checkout_session(
            customer_email=current_user.email,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        if checkout_session:
            # Redirect to Stripe Checkout
            logger.info(f"Redirecting {current_user.email} to Stripe Checkout: {checkout_session['session_id']}")
            return redirect(checkout_session['url'])
        else:
            # Fallback to payment link
            payment_link = payment_service.get_payment_link_url()
            logger.info(f"Redirecting {current_user.email} to payment link: {payment_link}")
            return redirect(payment_link)
            
    except Exception as e:
        logger.error(f"Error in subscribe route for {current_user.email}: {e}")
        flash("There was an error processing your request. Please try again.", "error")
        return redirect(url_for('main.index'))

@payments_bp.route('/payment/success')
@login_required
def payment_success():
    """
    Handle successful payment - show success page.
    """
    try:
        # Check if user now has an active subscription
        trial_status = trial_service.get_trial_status(current_user)
        
        logger.info(f"Payment success for {current_user.email} - subscription status: {trial_status['is_subscriber']}")
        
        # Clear any trial warnings from session
        if 'trial_warning_shown' in session:
            del session['trial_warning_shown']
        
        flash("Thank you! Your subscription is now active. Welcome to Waitlyst!", "success")
        return render_template('payment_success.html', trial_status=trial_status)
        
    except Exception as e:
        logger.error(f"Error in payment success for {current_user.email}: {e}")
        flash("Your payment was successful, but there was an error updating your account. Please contact support if you have issues.", "warning")
        return redirect(url_for('main.index'))

@payments_bp.route('/payment/cancelled')
@login_required  
def payment_cancelled():
    """
    Handle cancelled payment - show cancellation page with options.
    """
    try:
        trial_status = trial_service.get_trial_status(current_user)
        
        logger.info(f"Payment cancelled for {current_user.email}")
        
        flash("Payment was cancelled. You can try again anytime.", "info")
        return render_template('payment_cancelled.html', trial_status=trial_status)
        
    except Exception as e:
        logger.error(f"Error in payment cancelled for {current_user.email}: {e}")
        return redirect(url_for('main.index'))

# Billing portal removed - was causing errors

@payments_bp.route('/trial-status')
@login_required
def trial_status():
    """
    Show detailed trial and subscription status (useful for debugging).
    """
    try:
        trial_status = trial_service.get_trial_status(current_user)
        return render_template('trial_status.html', trial_status=trial_status)
        
    except Exception as e:
        logger.error(f"Error showing trial status for {current_user.email}: {e}")
        flash("Unable to load trial status.", "error")
        return redirect(url_for('main.index')) 