"""
Payment Routes - Handle Stripe payment flow
Provides endpoints for checkout, success, cancel, and billing portal.
"""

from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from flask_login import login_required, current_user
from src.services.payment_service import payment_service
from src.services.trial_service import trial_service
import logging
import stripe
import json
from src.config import Config

logger = logging.getLogger(__name__)

payments_bp = Blueprint('payments', __name__)

@payments_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events.
    This is where Stripe "rings the doorbell" to tell us about payments!
    """
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        # Verify that this request actually came from Stripe (security!)
        if Config.STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload, sig_header, Config.STRIPE_WEBHOOK_SECRET
            )
        else:
            # For local testing without webhook secret
            event = json.loads(payload)
            logger.warning("Processing webhook without signature verification (local testing only)")
        
        logger.info(f"🔔 Webhook received: {event['type']}")
        
        # Handle different types of "doorbell rings"
        if event['type'] == 'checkout.session.completed':
            # Someone just paid! 🎉
            session_obj = event['data']['object']
            customer_email = session_obj.get('customer_email')
            logger.info(f"💰 Payment successful for {customer_email}!")
            
        elif event['type'] == 'customer.subscription.created':
            # New subscription started 🚀
            subscription = event['data']['object']
            logger.info(f"🚀 New subscription created: {subscription.get('id')}")
            
        elif event['type'] == 'customer.subscription.deleted':
            # Subscription cancelled 😢
            subscription = event['data']['object']
            logger.info(f"😢 Subscription cancelled: {subscription.get('id')}")
            
        elif event['type'] == 'invoice.payment_failed':
            # Payment failed 💥
            invoice = event['data']['object']
            logger.warning(f"💥 Payment failed for customer: {invoice.get('customer')}")
            
        else:
            # Some other type of doorbell ring
            logger.info(f"🤷 Unhandled webhook type: {event['type']}")
        
        return 'success', 200
        
    except ValueError as e:
        # Invalid payload
        logger.error(f"❌ Invalid webhook payload: {e}")
        return 'Invalid payload', 400
        
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"❌ Invalid webhook signature: {e}")
        return 'Invalid signature', 400
        
    except Exception as e:
        # Something else went wrong
        logger.error(f"💥 Webhook error: {e}")
        return 'Webhook error', 500

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

@payments_bp.route('/billing-portal')
@login_required
def billing_portal():
    """
    Redirect to Stripe billing portal for subscription management.
    """
    try:
        # Check if user has a subscription
        trial_status = trial_service.get_trial_status(current_user)
        
        if not trial_status['is_subscriber']:
            flash("You need an active subscription to access the billing portal.", "error")
            return redirect(url_for('payments.subscribe'))
        
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
            flash("Unable to access billing portal. Please try again or contact support.", "error")
            return redirect(url_for('main.index'))
            
    except Exception as e:
        logger.error(f"Error accessing billing portal for {current_user.email}: {e}")
        flash("There was an error accessing the billing portal. Please try again.", "error")
        return redirect(url_for('main.index'))

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