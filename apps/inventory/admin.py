from django.contrib import admin

from .models import InventoryTransaction, ReorderLevel, StockRecord


@admin.register(StockRecord)
class StockRecordAdmin(admin.ModelAdmin):
    list_display = ["batch", "available_quantity", "reserved_quantity", "sellable_quantity"]
    search_fields = ["batch__product__name", "batch__batch_number"]


@admin.register(ReorderLevel)
class ReorderLevelAdmin(admin.ModelAdmin):
    list_display = ["product", "threshold"]
    search_fields = ["product__name"]


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ["batch", "transaction_type", "quantity_delta", "order", "created_at"]
    list_filter = ["transaction_type"]
    readonly_fields = [f.name for f in InventoryTransaction._meta.fields]

    def has_change_permission(self, request, obj=None):
        return False  # audit log is append-only
