from django.db import models

from apps.core.models import TimeStampedModel


class StockRecord(TimeStampedModel):
    """
    One row per product batch. `available_quantity` is what can be sold;
    `reserved_quantity` is held for orders that are Paid/Processing but not
    yet deducted permanently (e.g. mid-checkout race protection).
    """

    batch = models.OneToOneField(
        "catalog.ProductBatch", on_delete=models.CASCADE, related_name="stock_record"
    )
    available_quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "stock_records"

    @property
    def sellable_quantity(self):
        return max(self.available_quantity - self.reserved_quantity, 0)

    def __str__(self):
        return f"{self.batch} — avail {self.available_quantity} / reserved {self.reserved_quantity}"


class ReorderLevel(TimeStampedModel):
    """Per-product threshold that triggers a low-stock admin alert."""

    product = models.OneToOneField("catalog.Product", on_delete=models.CASCADE, related_name="reorder_level")
    threshold = models.PositiveIntegerField(default=10)

    class Meta:
        db_table = "reorder_levels"

    def __str__(self):
        return f"{self.product.name} reorder @ {self.threshold}"


class InventoryTransaction(TimeStampedModel):
    """
    Append-only audit log. Every stock mutation (restock, sale, reservation,
    release, manual adjustment, return) writes one row here — this is the
    source of truth for 'what happened to this stock and why'.
    """

    class TransactionType(models.TextChoices):
        RESTOCK = "RESTOCK", "Restock"
        RESERVE = "RESERVE", "Reserved for order"
        RELEASE = "RELEASE", "Reservation released"
        SALE_DEDUCT = "SALE_DEDUCT", "Deducted on payment success"
        RETURN = "RETURN", "Returned to stock"
        ADJUSTMENT = "ADJUSTMENT", "Manual admin adjustment"

    batch = models.ForeignKey("catalog.ProductBatch", on_delete=models.PROTECT, related_name="transactions")
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    quantity_delta = models.IntegerField(help_text="Positive for additions, negative for deductions.")
    order = models.ForeignKey(
        "orders.Order", null=True, blank=True, on_delete=models.SET_NULL, related_name="inventory_transactions"
    )
    performed_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="inventory_actions"
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "inventory_transactions"
        indexes = [models.Index(fields=["batch", "transaction_type"])]

    def __str__(self):
        return f"{self.transaction_type} {self.quantity_delta} — {self.batch}"
