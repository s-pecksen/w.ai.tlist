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
        """Initialize Stripe with API key."""
        stripe.api_key = Config.STRIPE_SECRET_KEY
        self.logger = logging.getLogger(__name__)
        
        if not Config.STRIPE_SECRET_KEY:
            self.logger.warning("STRIPE_SECRET_KEY not configured. Payment features will be disabled.")
    
    def create_checkout_session(self, customer_email: str, success_url: str, cancel_url: str) -> Optional[Dict[str, Any]]:
        """
        Create a Stripe Checkout session for subscription.
        
        Args:
            customer_email: Customer's email address
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if payment is cancelled
            
        Returns:
            Dict with checkout session data or None if error
        """
        try:
            if not Config.STRIPE_SECRET_KEY:
                self.logger.error("Cannot create checkout session: STRIPE_SECRET_KEY not configured")
                return None
            
            session_data = {
                'payment_method_types': ['card'],
                'mode': 'subscription',
                'customer_email': customer_email,
                'success_url': success_url,
                'cancel_url': cancel_url,
                'allow_promotion_codes': True,  # Allow discount codes
                'billing_address_collection': 'auto',
                'metadata': {
                    'customer_email': customer_email,
                    'product': 'waitlyst_subscription'
                }
            }
            
            # Use price ID if configured, otherwise use payment link
            if Config.STRIPE_PRICE_ID:
                session_data['line_items'] = [{
                    'price': Config.STRIPE_PRICE_ID,
                    'quantity': 1,
                }]
            else:
                self.logger.warning("STRIPE_PRICE_ID not configured. Using payment link fallback.")
                return None
            
            session = stripe.checkout.Session.create(**session_data)
            
            self.logger.info(f"Created checkout session for {customer_email}: {session.id}")
            
            return {
                'session_id': session.id,
                'url': session.url,
                'customer_email': customer_email
            }
            
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
        return Config.STRIPE_PAYMENT_LINK
    
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