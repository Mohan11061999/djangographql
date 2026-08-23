"""
Business logic for checkout kept out of schema.py so it's independently
testable and reusable from both GraphQL mutations and Celery tasks
(e.g. auto-cancelling unpaid orders after a timeout).
"""
import random
import string
from datetime import date

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from graphql import GraphQLError

from apps.catalog.models import Product
from apps.inventory.models import InventoryTransaction, StockRecord


def generate_order_number():
    date_part = timezone.now().strftime("%Y%m%d")
    random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"ORD-{date_part}-{random_part}"


def reserve_stock_for_item(product: Product, quantity: int, order):
    """
    Allocates `quantity` units from the product's batches, oldest expiry
    first (FIFO), so stock closest to expiring sells first. Creates a
    RESERVE inventory transaction per batch touched and returns a list of
    (batch, quantity_from_this_batch) tuples for OrderItem creation.

    Raises GraphQLError if there isn't enough sellable stock.
    """
    batches = (
        StockRecord.objects.select_for_update()
        .filter(batch__product=product, batch__expiration_date__gte=date.today())
        .select_related("batch")
        .order_by("batch__expiration_date")
    )

    remaining = quantity
    allocations = []

    for record in batches:
        if remaining <= 0:
            break
        take = min(remaining, record.sellable_quantity)
        if take <= 0:
            continue

        record.reserved_quantity += take
        record.save(update_fields=["reserved_quantity"])

        InventoryTransaction.objects.create(
            batch=record.batch,
            transaction_type=InventoryTransaction.TransactionType.RESERVE,
            quantity_delta=-take,
            order=order,
            notes="Reserved at checkout",
        )

        allocations.append((record.batch, take))
        remaining -= take

    if remaining > 0:
        raise GraphQLError(
            f"Insufficient stock for '{product.name}'. Only {quantity - remaining} unit(s) available."
        )

    return allocations


@transaction.atomic
def build_order_from_cart(*, user, cart, address, coupon=None, discount_amount=0, shipping_fee=0, order_number=None):
    """
    Creates a PENDING Order + OrderItems from the user's cart, reserving
    stock batch-by-batch. Does NOT touch Razorpay — the calling mutation
    creates the Razorpay order *before* calling this function (see
    apps.orders.schema.InitiateCheckout) so a payment-gateway failure
    never leaves an orphaned local Order with reserved stock.
    """
    from apps.orders.models import Order, OrderItem

    items = list(cart.items.select_related("product"))
    if not items:
        raise GraphQLError("Your cart is empty.")

    subtotal = sum((item.product.price * item.quantity for item in items), start=0)
    total_amount = subtotal - discount_amount + shipping_fee
    if total_amount < 0:
        raise GraphQLError("Invalid order total.")

    order = Order.objects.create(
        order_number=order_number or generate_order_number(),
        user=user,
        shipping_address=address,
        subtotal=subtotal,
        discount_amount=discount_amount,
        shipping_fee=shipping_fee,
        total_amount=total_amount,
        coupon_code=coupon.code if coupon else "",
    )

    for item in items:
        product = item.product
        if product.availability_status != Product.AvailabilityStatus.IN_STOCK:
            raise GraphQLError(f"'{product.name}' is no longer available.")

        allocations = reserve_stock_for_item(product, item.quantity, order)
        # An item can span multiple batches; create one OrderItem row per
        # batch so batch/expiry stays traceable per unit sold.
        for batch, qty in allocations:
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name_snapshot=product.name,
                unit_price_snapshot=product.price,
                quantity=qty,
                batch=batch,
            )

    return order


@transaction.atomic
def release_order_reservation(order):
    """
    Releases reserved (not yet deducted) stock back to availability.
    Used when an order is cancelled or its payment attempt is abandoned.
    """
    for item in order.items.select_related("batch"):
        if not item.batch:
            continue
        record = StockRecord.objects.select_for_update().get(batch=item.batch)
        record.reserved_quantity = max(record.reserved_quantity - item.quantity, 0)
        record.save(update_fields=["reserved_quantity"])

        InventoryTransaction.objects.create(
            batch=item.batch,
            transaction_type=InventoryTransaction.TransactionType.RELEASE,
            quantity_delta=item.quantity,
            order=order,
            notes="Reservation released (order cancelled/abandoned)",
        )


@transaction.atomic
def finalize_stock_deduction(order):
    """
    Called once payment is verified: permanently deducts the reserved
    stock (available_quantity -= qty, reserved_quantity -= qty), updates
    the product's units_sold counter, and flips availability_status to
    OUT_OF_STOCK if a product has no sellable stock left across all batches.
    """
    touched_products = set()

    for item in order.items.select_related("batch__product"):
        if not item.batch:
            continue
        record = StockRecord.objects.select_for_update().get(batch=item.batch)
        record.available_quantity = max(record.available_quantity - item.quantity, 0)
        record.reserved_quantity = max(record.reserved_quantity - item.quantity, 0)
        record.save(update_fields=["available_quantity", "reserved_quantity"])

        InventoryTransaction.objects.create(
            batch=item.batch,
            transaction_type=InventoryTransaction.TransactionType.SALE_DEDUCT,
            quantity_delta=-item.quantity,
            order=order,
            notes="Deducted on payment success",
        )
        touched_products.add(item.batch.product_id)

    for product_id in touched_products:
        product = Product.objects.select_for_update().get(id=product_id)
        product.units_sold = product.units_sold + sum(
            i.quantity for i in order.items.filter(batch__product_id=product_id)
        )
        remaining = StockRecord.objects.filter(batch__product_id=product_id).aggregate(
            total=Sum("available_quantity")
        )["total"] or 0
        if remaining <= 0:
            product.availability_status = Product.AvailabilityStatus.OUT_OF_STOCK
        product.save(update_fields=["units_sold", "availability_status"])
