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
    Handles both new registrations and existing user subscriptions.
    """
    try:
        # Check if this is from a new registration
        if 'pending_user_email' in session and 'just_registered' in session:
            # This is a new registration completing Stripe checkout
            email = session.pop('pending_user_email')
            session.pop('just_registered', None)
            
            # Find and log in the user
            from src.repositories.user_repository import UserRepository
            user_repo = UserRepository()
            user = user_repo.get_by_email(email)
            
            if user:
                from flask_login import login_user
                login_user(user)
                logger.info(f"New user {email} completed Stripe checkout and logged in successfully")
                flash("Welcome to Waitlyst! Your free trial has started.", "success")
            else:
                logger.error(f"Could not find user {email} after Stripe checkout")
                flash("There was an error with your registration. Please contact support.", "error")
                return redirect(url_for('auth.register'))
        
        elif 'pending_user_email' in session and 'login_after_checkout' in session:
            # This is an existing user completing required Stripe checkout at login
            email = session.pop('pending_user_email')
            session.pop('login_after_checkout', None)
            
            # Find and log in the user
            from src.repositories.user_repository import UserRepository
            user_repo = UserRepository()
            user = user_repo.get_by_email(email)
            
            if user:
                from flask_login import login_user
                login_user(user)
                logger.info(f"Existing user {email} completed required Stripe checkout and logged in")
                flash("Thank you for completing the setup! You now have access to Waitlyst.", "success")
            else:
                logger.error(f"Could not find user {email} after Stripe checkout during login")
                flash("There was an error logging you in. Please try again.", "error")
                return redirect(url_for('auth.login'))
        
        elif current_user.is_authenticated:
            # This is an existing user upgrading/subscribing
            logger.info(f"Existing user {current_user.email} completed payment")
            flash("Thank you! Your subscription has been updated.", "success")
        
        else:
            # Something went wrong - no session data and not logged in
            logger.warning("Payment success accessed without proper session or login")
            flash("Please log in to access your account.", "info")
            return redirect(url_for('auth.login'))
        
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