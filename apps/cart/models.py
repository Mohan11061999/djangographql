from django.db import models

from apps.core.models import TimeStampedModel


class Cart(TimeStampedModel):
    """One active cart per user, created lazily on first add-to-cart."""

    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="cart")

    class Meta:
        db_table = "carts"

    @property
    def subtotal(self):
        return sum((item.line_total for item in self.items.select_related("product")), start=0)

    def __str__(self):
        return f"Cart({self.user.email})"


class CartItem(TimeStampedModel):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="+")
    quantity = models.PositiveIntegerField(default=1)
    # Snapshot of unit price at time of adding, used only for display / change
    # detection ("price changed since you added this") — checkout always
    # recalculates from the live Product.price.
    unit_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "cart_items"
        unique_together = ("cart", "product")

    @property
    def line_total(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class Wishlist(TimeStampedModel):
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="wishlist")

    class Meta:
        db_table = "wishlists"


class WishlistItem(TimeStampedModel):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="+")

    class Meta:
        db_table = "wishlist_items"
        unique_together = ("wishlist", "product")
