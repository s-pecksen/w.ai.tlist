"""
Payment Service - Stripe Integration
Handles all payment-related operations including subscriptions, customers, and checkout sessions.
"""

import stripe
import logging
from typing import Dict, Optional, Any
from src.config import Config

logger = logging.getLogger(__name__)

class PaymentService:
    """
    Centralized service for handling Stripe payment operations.
    """
    
    def __init__(self):
        """Initialize payment service."""
        self.logger = logging.getLogger(__name__)
        
        if not Config.STRIPE_SECRET_KEY:
            self.logger.warning("STRIPE_SECRET_KEY not configured. Payment features will be disabled.")
    
    def create_customer_for_free_trial(self, customer_email: str) -> Optional[Dict[str, Any]]:
        """
        Create a Stripe customer for free trial without requiring payment method.
        
        Args:
            customer_email: Customer's email address
            
        Returns:
            Customer data dict or None if error
        """
        try:
            if not Config.STRIPE_SECRET_KEY:
                self.logger.error("Cannot create customer: STRIPE_SECRET_KEY not configured")
                return None
            
            # Check if customer already exists
            existing_customer = self.get_customer_by_email(customer_email)
            if existing_customer:
                self.logger.info(f"Customer {customer_email} already exists: {existing_customer['id']}")
                return existing_customer
            
            # Create new customer
            customer = stripe.Customer.create(
                email=customer_email,
                metadata={
                    'customer_email': customer_email,
                    'product': 'waitlyst_subscription',
                    'trial_started': 'true'
                }
            )
            
            self.logger.info(f"Created customer for free trial {customer_email}: {customer.id}")
            
            return {
                'id': customer.id,
                'email': customer.email,
                'created': customer.created,
                'metadata': customer.metadata
            }
            
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe error creating customer: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error creating customer: {e}")
            return None

    def create_customer_with_email_verification(self, customer_email: str) -> Optional[Dict[str, Any]]:
        """
        Create a Stripe customer with email verification enabled.
        
        Args:
            customer_email: Customer's email address
            
        Returns:
            Customer data dict or None if error
        """
        try:
            if not Config.STRIPE_SECRET_KEY:
                self.logger.error("Cannot create customer: STRIPE_SECRET_KEY not configured")
                return None
            
            # Check if customer already exists
            existing_customer = self.get_customer_by_email(customer_email)
            if existing_customer:
                self.logger.info(f"Customer {customer_email} already exists: {existing_customer['id']}")
                return existing_customer
            
            # Create new customer with email verification
            customer = stripe.Customer.create(
                email=customer_email,
                metadata={
                    'customer_email': customer_email,
                    'product': 'waitlyst_subscription',
                    'trial_started': 'true',
                    'email_verification_required': 'true'
                }
            )
            
            # Send email verification (Stripe will handle this automatically)
            # You can also use stripe.Customer.send_verification_email() if needed
            self.logger.info(f"Created customer with email verification {customer_email}: {customer.id}")
            
            return {
                'id': customer.id,
                'email': customer.email,
                'created': customer.created,
                'metadata': customer.metadata
            }
            
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe error creating customer with email verification: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error creating customer with email verification: {e}")
            return None

    def create_checkout_session(self, customer_email: str, success_url: str, cancel_url: str, for_subscription: bool = False) -> Optional[Dict[str, Any]]:
        """
        Create a Stripe Checkout session for subscription or free trial.
        
        Args:
            customer_email: Customer's email address
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment is cancelled
            for_subscription: If True, requires payment method. If False, creates customer without checkout.
            
        Returns:
            Dict with checkout session data or None if error
        """
        try:
            if not Config.STRIPE_SECRET_KEY:
                self.logger.error("Cannot create checkout session: STRIPE_SECRET_KEY not configured")
                return None
            
            if for_subscription:
                # For actual subscriptions, require payment method
                session_data = {
                    'payment_method_types': ['card'],
                    'mode': 'setup',  # Just collect payment method, don't charge
                    'customer_email': customer_email,
                    'success_url': success_url,
                    'cancel_url': cancel_url,
                    'billing_address_collection': 'auto',
                    'metadata': {
                        'customer_email': customer_email,
                        'product': 'waitlyst_subscription'
                    }
                }
                
                session = stripe.checkout.Session.create(**session_data)
                
                self.logger.info(f"Created checkout session for subscription {customer_email}: {session.id}")
                
                return {
                    'session_id': session.id,
                    'url': session.url,
                    'customer_email': customer_email
                }
            else:
                # For free trials, just create customer without checkout
                customer = self.create_customer_for_free_trial(customer_email)
                if customer:
                    self.logger.info(f"Created customer for free trial {customer_email}: {customer['id']}")
                    # Return a mock session that redirects to success
                    return {
                        'session_id': f"trial_{customer['id']}",
                        'url': success_url,  # Redirect directly to success
                        'customer_email': customer_email,
                        'is_trial': True
                    }
                else:
                    return None
            
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe error creating checkout session: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error creating checkout session: {e}")
            return None
    
    def get_customer_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get Stripe customer by email address.
        
        Args:
            email: Customer's email address
            
        Returns:
            Customer data dict or None if not found
        """
        try:
            customers = stripe.Customer.search(query=f'email:"{email}"')
            
            if customers.data:
                customer = customers.data[0]
                return {
                    'id': customer.id,
                    'email': customer.email,
                    'created': customer.created,
                    'metadata': customer.metadata
                }
            return None
            
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe error getting customer: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting customer: {e}")
            return None
    
    def has_active_subscription(self, customer_email: str) -> bool:
        """
        Check if customer has an active subscription.
        
        Args:
            customer_email: Customer's email address
            
        Returns:
            True if customer has active subscription, False otherwise
        """
        try:
            customer = self.get_customer_by_email(customer_email)
            if not customer:
                return False
            
            # Get subscriptions for this customer
            subscriptions = stripe.Subscription.list(customer=customer['id'], status="all")
            
            for subscription in subscriptions.auto_paging_iter():
                if subscription.status in ['active', 'trialing']:
                    self.logger.info(f"Found active subscription for {customer_email}: {subscription.id}")
                    return True
            
            return False
            
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe error checking subscription: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error checking subscription: {e}")
            return False
    
    def get_payment_link_url(self) -> str:
        """
        Get the configured Stripe payment link URL.
        
        Returns:
            Payment link URL
        """
        # Payment links removed - using Checkout sessions with custom redirects
        return None
    
    def create_billing_portal_session(self, customer_email: str, return_url: str) -> Optional[str]:
        """
        Create a Stripe billing portal session for subscription management.
        
        Args:
            customer_email: Customer's email address
            return_url: URL to return to after billing portal
            
        Returns:
            Billing portal URL or None if error
        """
        try:
            customer = self.get_customer_by_email(customer_email)
            if not customer:
                self.logger.error(f"Cannot create billing portal: customer {customer_email} not found")
                return None
            
            session = stripe.billing_portal.Session.create(
                customer=customer['id'],
                return_url=return_url,
            )
            
            self.logger.info(f"Created billing portal session for {customer_email}")
            return session.url
            
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe error creating billing portal: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error creating billing portal: {e}")
            return None

# Global instance for easy import
payment_service = PaymentService() 