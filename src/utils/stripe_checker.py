import stripe
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get Stripe API key from environment variable
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

def has_active_subscription(customer_email):
    # 1. Search for customer by email
    customers = stripe.Customer.search(
        query=f'email:"{customer_email}"'
    )

    if not customers.data:
        return None  # No customer found

    customer_id = customers.data[0].id

    # 2. List subscriptions for this customer, check for active one (including free subscriptions)
    subscriptions = stripe.Subscription.list(customer=customer_id, status="all")
    for sub in subscriptions.auto_paging_iter():
        # Check if subscription is active (including free subscriptions)
        if sub.status == "active":
            return True
        # Also check for trialing subscriptions which are considered active
        elif sub.status == "trialing":
            return True

    return False