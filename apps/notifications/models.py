from django.db import models

from apps.core.models import TimeStampedModel


class EmailLog(TimeStampedModel):
    class EmailType(models.TextChoices):
        REGISTRATION = "REGISTRATION", "Registration welcome"
        EMAIL_VERIFICATION = "EMAIL_VERIFICATION", "Email verification"
        PASSWORD_RESET = "PASSWORD_RESET", "Password reset"
        ORDER_CONFIRMATION = "ORDER_CONFIRMATION", "Order confirmation"
        PAYMENT_RECEIPT = "PAYMENT_RECEIPT", "Payment receipt"
        SHIPMENT_TRACKING = "SHIPMENT_TRACKING", "Shipment tracking"
        DELIVERY_CONFIRMATION = "DELIVERY_CONFIRMATION", "Delivery confirmation"
        LOW_STOCK_ALERT = "LOW_STOCK_ALERT", "Admin low stock alert"

    email_type = models.CharField(max_length=30, choices=EmailType.choices)
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    related_order = models.ForeignKey(
        "orders.Order", null=True, blank=True, on_delete=models.SET_NULL, related_name="email_logs"
    )
    was_successful = models.BooleanField(default=True)
    error_message = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "email_logs"
        indexes = [models.Index(fields=["email_type", "recipient"])]
