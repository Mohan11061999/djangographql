from django.db import models

from apps.core.models import TimeStampedModel


class PaymentTransaction(TimeStampedModel):
    """
    One row per Razorpay order attempt. A single Order can have multiple
    PaymentTransaction rows if a payment fails and the customer retries —
    only one should ever end up VERIFIED.
    """

    class Method(models.TextChoices):
        UPI = "UPI", "UPI"
        CARD = "CARD", "Card"
        NETBANKING = "NETBANKING", "Net Banking"
        WALLET = "WALLET", "Wallet"
        UNKNOWN = "UNKNOWN", "Unknown"

    class Status(models.TextChoices):
        CREATED = "CREATED", "Order created, awaiting payment"
        VERIFIED = "VERIFIED", "Signature verified — payment successful"
        FAILED = "FAILED", "Payment failed"
        SIGNATURE_MISMATCH = "SIGNATURE_MISMATCH", "Signature verification failed"
        REFUNDED = "REFUNDED", "Refunded"

    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="payment_transactions")

    razorpay_order_id = models.CharField(max_length=100, db_index=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, db_index=True)
    razorpay_signature = models.CharField(max_length=255, blank=True)

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.UNKNOWN)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.CREATED)

    # Raw webhook/callback payload retained for dispute resolution & debugging.
    raw_response = models.JSONField(default=dict, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "payment_transactions"
        indexes = [models.Index(fields=["order", "status"])]

    def __str__(self):
        return f"{self.razorpay_order_id} — {self.status}"


class Invoice(TimeStampedModel):
    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="invoice")
    invoice_number = models.CharField(max_length=30, unique=True)
    pdf_file = models.FileField(upload_to="invoices/", null=True, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "invoices"

    def __str__(self):
        return self.invoice_number
