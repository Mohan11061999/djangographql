from django.contrib import admin

from .models import Cart, CartItem, Wishlist, WishlistItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["user", "updated_at"]
    inlines = [CartItemInline]
    search_fields = ["user__email"]


class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 0


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ["user", "updated_at"]
    inlines = [WishlistItemInline]
    search_fields = ["user__email"]
