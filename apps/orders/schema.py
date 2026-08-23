import graphene
from decimal import Decimal
from django.db import transaction
from graphene_django import DjangoObjectType
from graphql import GraphQLError

from apps.accounts.models import Address
from apps.core.permissions import admin_required, login_required, verified_email_required
from apps.coupons.models import Coupon, CouponRedemption
from apps.payments.invoicing import create_invoice_for_order
from apps.payments.models import PaymentTransaction
from apps.payments.services import create_razorpay_order, fetch_payment_details, verify_payment_signature
from .models import Order, OrderItem, OrderStatusHistory, ShipmentTracking
from .services import build_order_from_cart, finalize_stock_deduction, release_order_reservation


class OrderItemType(DjangoObjectType):
    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name_snapshot", "unit_price_snapshot", "quantity", "batch"]

    line_total = graphene.Decimal()

    def resolve_line_total(self, info):
        return self.line_total


class OrderStatusHistoryType(DjangoObjectType):
    class Meta:
        model = OrderStatusHistory
        fields = ["id", "status", "notes", "created_at"]


class ShipmentTrackingType(DjangoObjectType):
    class Meta:
        model = ShipmentTracking
        fields = [
            "id", "courier_name", "tracking_number", "dispatch_date",
            "expected_delivery_date", "actual_delivery_date", "notes",
        ]


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = [
            "id", "order_number", "user", "shipping_address", "status",
            "subtotal", "discount_amount", "shipping_fee", "total_amount",
            "coupon_code", "placed_at", "items", "status_history", "shipment",
        ]


class PaymentTransactionType(DjangoObjectType):
    class Meta:
        model = PaymentTransaction
        fields = [
            "id", "razorpay_order_id", "razorpay_payment_id", "amount",
            "currency", "method", "status", "verified_at", "created_at",
        ]


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------
class OrdersQuery(graphene.ObjectType):
    my_orders = graphene.List(OrderType)
    order = graphene.Field(OrderType, order_number=graphene.String(required=True))

    # Admin
    all_orders = graphene.List(OrderType, status=graphene.String())

    @login_required
    def resolve_my_orders(root, info):
        return Order.objects.filter(user=info.context.user).order_by("-placed_at")

    @login_required
    def resolve_order(root, info, order_number):
        user = info.context.user
        qs = Order.objects.all() if user.is_admin else Order.objects.filter(user=user)
        try:
            return qs.get(order_number=order_number)
        except Order.DoesNotExist:
            raise GraphQLError("Order not found.")

    @admin_required
    def resolve_all_orders(root, info, status=None):
        qs = Order.objects.all().order_by("-placed_at")
        if status:
            qs = qs.filter(status=status)
        return qs


# ---------------------------------------------------------------------------
# Checkout: Step 1 — create order + Razorpay order (server-verified later)
# ---------------------------------------------------------------------------
class InitiateCheckout(graphene.Mutation):
    """
    Checkout workflow step: Cart -> Address Selection -> Coupon Validation
    -> [this mutation] Order Summary -> Payment.

    Creates a PENDING Order with reserved stock and a matching Razorpay
    order. The frontend uses the returned razorpay_order_id/amount/key to
    open the Razorpay Checkout widget; nothing here is treated as a
    successful payment yet.
    """

    class Arguments:
        address_id = graphene.ID(required=True)
        coupon_code = graphene.String()
        shipping_fee = graphene.Decimal(default_value=Decimal("0"))

    ok = graphene.Boolean()
    order = graphene.Field(OrderType)
    razorpay_order_id = graphene.String()
    razorpay_key_id = graphene.String()
    amount_paise = graphene.Int()

    @verified_email_required
    def mutate(root, info, address_id, shipping_fee, coupon_code=None):
        from apps.cart.models import Cart
        from django.conf import settings

        from .services import generate_order_number

        user = info.context.user

        try:
            address = Address.objects.get(id=address_id, user=user)
        except Address.DoesNotExist:
            raise GraphQLError("Shipping address not found.")

        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            raise GraphQLError("Your cart is empty.")

        if not cart.items.exists():
            raise GraphQLError("Your cart is empty.")

        coupon = None
        discount_amount = 0
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code__iexact=coupon_code.strip())
            except Coupon.DoesNotExist:
                raise GraphQLError("Invalid coupon code.")
            if not coupon.is_valid_now():
                raise GraphQLError("This coupon is expired or no longer active.")
            per_user_uses = CouponRedemption.objects.filter(coupon=coupon, user=user).count()
            if per_user_uses >= coupon.usage_limit_per_user:
                raise GraphQLError("You have already used this coupon.")
            discount_amount = coupon.calculate_discount(cart.subtotal)

        subtotal = cart.subtotal
        total_amount = subtotal - discount_amount + shipping_fee
        if total_amount < 0:
            raise GraphQLError("Invalid order total.")

        # IMPORTANT: the Razorpay API call happens BEFORE any local writes.
        # If this call fails (network error, bad credentials, etc.) nothing
        # has been written to our database yet — no dangling order, no
        # reserved-but-unpaid stock, and the cart is untouched so the
        # customer can simply retry. Everything after this line is wrapped
        # in one atomic transaction.
        order_number = generate_order_number()
        razorpay_order = create_razorpay_order(amount_rupees=total_amount, receipt=order_number)

        with transaction.atomic():
            order = build_order_from_cart(
                user=user, cart=cart, address=address, coupon=coupon,
                discount_amount=discount_amount, shipping_fee=shipping_fee,
                order_number=order_number,
            )

            PaymentTransaction.objects.create(
                order=order,
                razorpay_order_id=razorpay_order["id"],
                amount=order.total_amount,
                status=PaymentTransaction.Status.CREATED,
                raw_response=razorpay_order,
            )

            if coupon:
                CouponRedemption.objects.create(coupon=coupon, user=user, order=order)
                Coupon.objects.filter(id=coupon.id).update(times_used=coupon.times_used + 1)

            # Cart is cleared only once the order + reservation is safely
            # committed, so a page refresh mid-payment can't let the
            # customer re-add and double-reserve the same stock.
            cart.items.all().delete()

        return InitiateCheckout(
            ok=True,
            order=order,
            razorpay_order_id=razorpay_order["id"],
            razorpay_key_id=settings.RAZORPAY_KEY_ID,
            amount_paise=razorpay_order["amount"],
        )


# ---------------------------------------------------------------------------
# Checkout: Step 2 — mandatory server-side signature verification
# ---------------------------------------------------------------------------
class VerifyPayment(graphene.Mutation):
    """
    The client's "payment succeeded" callback is NEVER trusted on its own.
    This mutation re-verifies the HMAC signature against Razorpay's own
    secret before touching order/inventory state, per the spec's security
    requirement.
    """

    class Arguments:
        razorpay_order_id = graphene.String(required=True)
        razorpay_payment_id = graphene.String(required=True)
        razorpay_signature = graphene.String(required=True)

    ok = graphene.Boolean()
    order = graphene.Field(OrderType)

    @login_required
    @transaction.atomic
    def mutate(root, info, razorpay_order_id, razorpay_payment_id, razorpay_signature):
        try:
            txn = PaymentTransaction.objects.select_for_update().select_related("order").get(
                razorpay_order_id=razorpay_order_id, order__user=info.context.user
            )
        except PaymentTransaction.DoesNotExist:
            raise GraphQLError("Payment record not found.")

        is_valid = verify_payment_signature(
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
        )

        if not is_valid:
            txn.status = PaymentTransaction.Status.SIGNATURE_MISMATCH
            txn.razorpay_payment_id = razorpay_payment_id
            txn.save(update_fields=["status", "razorpay_payment_id"])
            raise GraphQLError("Payment verification failed. If money was deducted, it will be refunded.")

        # Signature is valid — now safe to mark paid and mutate state.
        payment_details = fetch_payment_details(razorpay_payment_id)
        method_map = {
            "upi": PaymentTransaction.Method.UPI,
            "card": PaymentTransaction.Method.CARD,
            "netbanking": PaymentTransaction.Method.NETBANKING,
            "wallet": PaymentTransaction.Method.WALLET,
        }

        from django.utils import timezone

        txn.status = PaymentTransaction.Status.VERIFIED
        txn.razorpay_payment_id = razorpay_payment_id
        txn.razorpay_signature = razorpay_signature
        txn.method = method_map.get(payment_details.get("method"), PaymentTransaction.Method.UNKNOWN)
        txn.raw_response = payment_details
        txn.verified_at = timezone.now()
        txn.save()

        order = txn.order
        finalize_stock_deduction(order)
        order.transition_to(Order.Status.PAID, notes="Payment verified via Razorpay", changed_by=info.context.user)

        invoice = create_invoice_for_order(order)

        from apps.notifications.tasks import (
            notify_admin_new_order_task,
            send_order_confirmation_task,
            send_payment_receipt_task,
        )

        send_order_confirmation_task.delay(str(order.id))
        send_payment_receipt_task.delay(str(order.id), str(invoice.id))
        notify_admin_new_order_task.delay(str(order.id))

        return VerifyPayment(ok=True, order=order)


class CancelOrder(graphene.Mutation):
    """Allowed only while an order hasn't been paid yet; releases reserved stock."""

    class Arguments:
        order_number = graphene.String(required=True)
        reason = graphene.String()

    ok = graphene.Boolean()

    @login_required
    def mutate(root, info, order_number, reason=""):
        try:
            order = Order.objects.get(order_number=order_number, user=info.context.user)
        except Order.DoesNotExist:
            raise GraphQLError("Order not found.")

        if order.status != Order.Status.PENDING:
            raise GraphQLError("Only pending (unpaid) orders can be cancelled by the customer.")

        release_order_reservation(order)
        order.transition_to(Order.Status.CANCELLED, notes=reason or "Cancelled by customer", changed_by=info.context.user)
        return CancelOrder(ok=True)


# ---------------------------------------------------------------------------
# Admin: order status + manual courier shipment workflow
# ---------------------------------------------------------------------------
ALLOWED_ADMIN_TRANSITIONS = {
    Order.Status.PAID: {Order.Status.PROCESSING, Order.Status.CANCELLED, Order.Status.REFUNDED},
    Order.Status.PROCESSING: {Order.Status.PACKED, Order.Status.CANCELLED},
    Order.Status.PACKED: {Order.Status.SHIPPED},
    Order.Status.SHIPPED: {Order.Status.OUT_FOR_DELIVERY},
    Order.Status.OUT_FOR_DELIVERY: {Order.Status.DELIVERED},
    Order.Status.DELIVERED: {Order.Status.REFUNDED},
}


class UpdateOrderStatus(graphene.Mutation):
    class Arguments:
        order_number = graphene.String(required=True)
        new_status = graphene.String(required=True)
        notes = graphene.String()

    ok = graphene.Boolean()
    order = graphene.Field(OrderType)

    @admin_required
    def mutate(root, info, order_number, new_status, notes=""):
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            raise GraphQLError("Order not found.")

        allowed = ALLOWED_ADMIN_TRANSITIONS.get(order.status, set())
        if new_status not in allowed:
            raise GraphQLError(f"Cannot transition order from {order.status} to {new_status}.")

        order.transition_to(new_status, notes=notes, changed_by=info.context.user)
        return UpdateOrderStatus(ok=True, order=order)


class AddShipmentTracking(graphene.Mutation):
    """
    Manual courier workflow: Payment Verified -> Admin Packages Order ->
    Ships via Manual Courier -> [this mutation] -> Customer Notified.
    """

    class Arguments:
        order_number = graphene.String(required=True)
        courier_name = graphene.String(required=True)
        tracking_number = graphene.String(required=True)
        dispatch_date = graphene.Date(required=True)
        expected_delivery_date = graphene.Date()

    ok = graphene.Boolean()
    shipment = graphene.Field(ShipmentTrackingType)

    @admin_required
    def mutate(root, info, order_number, courier_name, tracking_number, dispatch_date, expected_delivery_date=None):
        try:
            order = Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            raise GraphQLError("Order not found.")

        if order.status not in {Order.Status.PACKED, Order.Status.PROCESSING}:
            raise GraphQLError("Order must be packed before it can be shipped.")

        shipment, _ = ShipmentTracking.objects.update_or_create(
            order=order,
            defaults={
                "courier_name": courier_name,
                "tracking_number": tracking_number,
                "dispatch_date": dispatch_date,
                "expected_delivery_date": expected_delivery_date,
            },
        )

        order.transition_to(
            Order.Status.SHIPPED, notes=f"Shipped via {courier_name}", changed_by=info.context.user
        )

        from apps.notifications.tasks import send_shipment_tracking_task

        send_shipment_tracking_task.delay(str(order.id))

        return AddShipmentTracking(ok=True, shipment=shipment)


class MarkDelivered(graphene.Mutation):
    class Arguments:
        order_number = graphene.String(required=True)
        actual_delivery_date = graphene.Date(required=True)

    ok = graphene.Boolean()

    @admin_required
    def mutate(root, info, order_number, actual_delivery_date):
        try:
            order = Order.objects.select_related("shipment").get(order_number=order_number)
        except Order.DoesNotExist:
            raise GraphQLError("Order not found.")

        if hasattr(order, "shipment"):
            order.shipment.actual_delivery_date = actual_delivery_date
            order.shipment.save(update_fields=["actual_delivery_date"])

        order.transition_to(Order.Status.DELIVERED, changed_by=info.context.user)

        from apps.notifications.tasks import send_delivery_confirmation_task

        send_delivery_confirmation_task.delay(str(order.id))

        return MarkDelivered(ok=True)


class OrdersMutation(graphene.ObjectType):
    initiate_checkout = InitiateCheckout.Field()
    verify_payment = VerifyPayment.Field()
    cancel_order = CancelOrder.Field()

    update_order_status = UpdateOrderStatus.Field()
    add_shipment_tracking = AddShipmentTracking.Field()
    mark_delivered = MarkDelivered.Field()
