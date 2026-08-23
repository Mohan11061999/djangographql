from django.contrib import admin

from .models import Coupon, CouponRedemption


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ["code", "discount_type", "discount_value", "valid_until", "times_used", "is_active"]
    list_filter = ["discount_type", "is_active"]
    search_fields = ["code"]


admin.site.register(CouponRedemption)
