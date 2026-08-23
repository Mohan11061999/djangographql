from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class Coupon(TimeStampedModel):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "PERCENTAGE", "Percentage"
        FIXED = "FIXED", "Fixed amount"

    code = models.CharField(max_length=32, unique=True, db_index=True)
    description = models.CharField(max_length=255, blank=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    max_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Caps the discount for PERCENTAGE coupons, e.g. 20% off up to ₹200.",
    )
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField()

    usage_limit_total = models.PositiveIntegerField(null=True, blank=True, help_text="Overall redemption cap.")
    usage_limit_per_user = models.PositiveIntegerField(default=1)
    times_used = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "coupons"

    def clean(self):
        if self.discount_type == self.DiscountType.PERCENTAGE and not (0 < self.discount_value <= 100):
            raise ValidationError("Percentage discount must be between 0 and 100.")
        if self.valid_until <= self.valid_from:
            raise ValidationError("valid_until must be after valid_from.")

    def is_valid_now(self):
        now = timezone.now()
        if not self.is_active or not (self.valid_from <= now <= self.valid_until):
            return False
        if self.usage_limit_total is not None and self.times_used >= self.usage_limit_total:
            return False
        return True

    def calculate_discount(self, order_subtotal):
        from decimal import Decimal

        if order_subtotal < self.min_order_value:
            return Decimal("0")
        if self.discount_type == self.DiscountType.FIXED:
            return min(self.discount_value, order_subtotal)
        discount = order_subtotal * (self.discount_value / Decimal("100"))
        if self.max_discount_amount is not None:
            discount = min(discount, self.max_discount_amount)
        return discount

    def __str__(self):
        return self.code


class CouponRedemption(TimeStampedModel):
    """Tracks per-user usage so usage_limit_per_user can be enforced."""

    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="redemptions")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="coupon_redemptions")
    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="coupon_redemption")

    class Meta:
        db_table = "coupon_redemptions"
