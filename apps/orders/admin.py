from django.contrib import admin

from .models import Order, OrderItem, OrderStatusHistory, ShipmentTracking


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["product_name_snapshot", "unit_price_snapshot", "quantity", "batch"]


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ["status", "notes", "changed_by", "created_at"]


class ShipmentTrackingInline(admin.StackedInline):
    model = ShipmentTracking
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_number", "user", "status", "total_amount", "placed_at"]
    list_filter = ["status"]
    search_fields = ["order_number", "user__email"]
    inlines = [OrderItemInline, ShipmentTrackingInline, OrderStatusHistoryInline]
    readonly_fields = ["subtotal", "discount_amount", "total_amount", "placed_at"]

    def save_formset(self, request, form, formset, change):
        """When admin fills in ShipmentTracking inline, auto-transition to SHIPPED."""
        instances = formset.save(commit=False)
        for instance in instances:
            instance.save()
            if isinstance(instance, ShipmentTracking):
                order = instance.order
                if order.status not in [Order.Status.SHIPPED, Order.Status.OUT_FOR_DELIVERY, Order.Status.DELIVERED]:
                    order.transition_to(Order.Status.SHIPPED, notes="Courier details entered by admin", changed_by=request.user)
        formset.save_m2m()
