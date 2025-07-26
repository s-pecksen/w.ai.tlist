"""
Payment Routes - Handle Stripe payment flow
Provides endpoints for checkout, success, cancel, and billing portal.
"""

from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from flask_login import login_required, current_user
from src.decorators.trial_required import trial_required
from src.services.payment_service import payment_service
from src.services.trial_service import trial_service
import logging

logger = logging.getLogger(__name__)

payments_bp = Blueprint('payments', __name__)

# Webhook routes moved to main app.py for better reliability with Stripe deliveries

@payments_bp.route('/subscribe', methods=['GET'])
@trial_required
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
        
        # Try to create a checkout session for subscription (requires payment method)
        checkout_session = payment_service.create_checkout_session(
            customer_email=current_user.email,
            success_url=success_url,
            cancel_url=cancel_url,
            for_subscription=True  # Actual subscription - payment method required
        )
        
        if checkout_session:
            # Redirect to Stripe Checkout for subscription
            logger.info(f"Redirecting {current_user.email} to Stripe Checkout: {checkout_session['session_id']}")
            return redirect(checkout_session['url'])
        else:
            # Checkout session creation failed
            logger.error(f"Failed to create checkout session for {current_user.email}")
            flash("There was an error processing your request. Please try again.", "error")
            return redirect(url_for('main.index'))
            
    except Exception as e:
        logger.error(f"Error in subscribe route for {current_user.email}: {e}")
        flash("There was an error processing your request. Please try again.", "error")
        return redirect(url_for('main.index'))

@payments_bp.route('/payment/success')
@login_required
def payment_success():
    """
    Handle successful payment - show success page.
    Handles both new registrations and existing user subscriptions.
    """
    try:
        # This route is now primarily for subscription payments, not free trial setup
        # Free trial setup is handled directly in auth routes
        
        if current_user.is_authenticated:
            # This is an existing user upgrading/subscribing
            logger.info(f"Existing user {current_user.email} completed payment")
            flash("Thank you! Your subscription has been updated.", "success")
        else:
            # Something went wrong - not logged in
            logger.warning("Payment success accessed without login")
            flash("Please log in to access your account.", "info")
            return redirect(url_for('auth.login'))
        
        # Clear any accumulated session data
        session.pop('pending_user_email', None)
        session.pop('just_registered', None)
        session.pop('login_after_checkout', None)
        
        # Get trial status for display (user should be logged in by now)
        if current_user.is_authenticated:
            trial_status = trial_service.get_trial_status(current_user)
            
            # Clear any trial warnings from session
            if 'trial_warning_shown' in session:
                del session['trial_warning_shown']
            
            # Check if user was trying to access a specific page
            next_url = session.pop('next_url', None)
            if next_url and next_url != request.url:
                # Redirect them back to where they were trying to go
                logger.info(f"Redirecting {current_user.email} back to intended destination: {next_url}")
                return redirect(next_url)
            else:
                # Show success page
                return render_template('payment_success.html', trial_status=trial_status)
        else:
            return redirect(url_for('auth.login'))
        
    except Exception as e:
        logger.error(f"Error in payment success: {e}")
        flash("Your payment was successful, but there was an error. Please contact support if you have issues.", "warning")
        return redirect(url_for('auth.login'))

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

@payments_bp.route('/billing-portal')
@login_required
def billing_portal():
    """
    Redirect user to Stripe billing portal to manage subscription and payment methods.
    """
    try:
        # Create billing portal session
        return_url = request.url_root.rstrip('/') + url_for('main.index')
        portal_url = payment_service.create_billing_portal_session(
            customer_email=current_user.email,
            return_url=return_url
        )
        
        if portal_url:
            logger.info(f"Redirecting {current_user.email} to billing portal")
            return redirect(portal_url)
        else:
            flash("Unable to access billing portal. Please contact support.", "error")
            return redirect(url_for('main.index'))
            
    except Exception as e:
        logger.error(f"Error creating billing portal session for {current_user.email}: {e}")
        flash("There was an error accessing the billing portal. Please try again.", "error")
        return redirect(url_for('main.index'))

@payments_bp.route('/trial-status')
@trial_required
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