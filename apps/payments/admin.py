from django.contrib import admin

from .models import Invoice, PaymentTransaction


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ["razorpay_order_id", "razorpay_payment_id", "order", "amount", "status", "created_at"]
    list_filter = ["status", "method"]
    search_fields = ["razorpay_order_id", "razorpay_payment_id", "order__order_number"]
    readonly_fields = [f.name for f in PaymentTransaction._meta.fields]

    def has_change_permission(self, request, obj=None):
        return False  # payment records are immutable once written


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "order", "issued_at"]
    search_fields = ["invoice_number", "order__order_number"]
