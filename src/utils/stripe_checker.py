"""
Stripe Subscription Checker - Updated to use PaymentService
Maintains backward compatibility while using the new centralized payment service.
"""

import logging
from src.services.payment_service import payment_service

logger = logging.getLogger(__name__)

def has_active_subscription(customer_email):
    """
    Check if customer has an active Stripe subscription.
    
    Args:
        customer_email: Customer's email address
        
    Returns:
        bool: True if customer has active subscription, False otherwise
    """
    try:
        return payment_service.has_active_subscription(customer_email)
    except Exception as e:
        logger.error(f"Error checking subscription for {customer_email}: {e}")
        return False