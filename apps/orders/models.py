from django.db import models

from apps.core.models import TimeStampedModel


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        PROCESSING = "PROCESSING", "Processing"
        PACKED = "PACKED", "Packed"
        SHIPPED = "SHIPPED", "Shipped"
        OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for Delivery"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"
        REFUNDED = "REFUNDED", "Refunded"

    order_number = models.CharField(max_length=20, unique=True, db_index=True)
    user = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="orders")
    shipping_address = models.ForeignKey(
        "accounts.Address", on_delete=models.PROTECT, related_name="+"
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    coupon_code = models.CharField(max_length=32, blank=True)

    placed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "orders"
        indexes = [models.Index(fields=["user", "status"]), models.Index(fields=["-placed_at"])]

    def __str__(self):
        return self.order_number

    def transition_to(self, new_status, *, notes="", changed_by=None):
        """
        Central place for status changes so the history log is never
        forgotten. Always call this instead of setting .status directly.
        """
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])
        OrderStatusHistory.objects.create(order=self, status=new_status, notes=notes, changed_by=changed_by)


class OrderItem(TimeStampedModel):
    """
    Product name/price are snapshotted at order time so historical orders
    display correctly even if the product is later renamed, repriced, or
    discontinued.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="order_items")
    product_name_snapshot = models.CharField(max_length=255)
    unit_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    batch = models.ForeignKey(
        "catalog.ProductBatch", null=True, blank=True, on_delete=models.SET_NULL, related_name="order_items"
    )

    class Meta:
        db_table = "order_items"

    @property
    def line_total(self):
        return self.unit_price_snapshot * self.quantity


class OrderStatusHistory(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    status = models.CharField(max_length=20, choices=Order.Status.choices)
    notes = models.CharField(max_length=255, blank=True)
    changed_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        db_table = "order_status_history"
        ordering = ["created_at"]
        verbose_name_plural = "order status histories"


class ShipmentTracking(TimeStampedModel):
    """
    Manual courier workflow: admin fills this in once a package is
    dispatched. No live carrier API integration — tracking number is just
    stored text the customer can look up on the courier's own site.
    """

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="shipment")
    courier_name = models.CharField(max_length=150)
    tracking_number = models.CharField(max_length=100)
    dispatch_date = models.DateField()
    expected_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "shipment_tracking"

    def __str__(self):
        return f"{self.courier_name} — {self.tracking_number}"
