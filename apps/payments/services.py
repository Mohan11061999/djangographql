"""
All Razorpay API interaction is isolated here. The cardinal rule from the
spec: NEVER trust client-side payment responses — verify_payment_signature
must pass before any order/inventory state changes.
"""
import razorpay
from django.conf import settings


def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_razorpay_order(*, amount_rupees, receipt):
    """
    amount_rupees is a Decimal/float rupee amount; Razorpay's API wants
    the smallest currency unit (paise), so we multiply by 100 and round
    to an int to avoid floating point drift.
    """
    client = get_razorpay_client()
    amount_paise = int(round(float(amount_rupees) * 100))
    return client.order.create(
        {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "payment_capture": 1,
        }
    )


def verify_payment_signature(*, razorpay_order_id, razorpay_payment_id, razorpay_signature):
    """
    Returns True only if Razorpay's HMAC signature check passes. This is
    the ONLY source of truth for "did this payment really succeed" —
    client-supplied 'success' flags are never trusted.
    """
    client = get_razorpay_client()
    try:
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )
        return True
    except razorpay.errors.SignatureVerificationError:
        return False


def fetch_payment_details(razorpay_payment_id):
    """Used after verification to record the actual payment method used (UPI/card/etc)."""
    client = get_razorpay_client()
    return client.payment.fetch(razorpay_payment_id)


def initiate_refund(razorpay_payment_id, amount_rupees=None):
    client = get_razorpay_client()
    payload = {}
    if amount_rupees is not None:
        payload["amount"] = int(round(float(amount_rupees) * 100))
    return client.payment.refund(razorpay_payment_id, payload)
