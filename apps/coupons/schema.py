import graphene
from graphene_django import DjangoObjectType
from graphql import GraphQLError

from apps.core.permissions import admin_required, login_required
from .models import Coupon


class CouponType(DjangoObjectType):
    class Meta:
        model = Coupon
        fields = [
            "id", "code", "description", "discount_type", "discount_value",
            "max_discount_amount", "min_order_value", "valid_from", "valid_until",
            "usage_limit_total", "usage_limit_per_user", "times_used", "is_active",
        ]


class ValidateCoupon(graphene.Mutation):
    """
    Called from the checkout page (Cart -> Address -> Coupon step) before
    order creation. Returns the discount amount for the user's current
    cart subtotal without redeeming the coupon yet — redemption is
    recorded only once the order is actually placed (see orders.schema).
    """

    class Arguments:
        code = graphene.String(required=True)

    ok = graphene.Boolean()
    discount_amount = graphene.Decimal()
    error = graphene.String()

    @login_required
    def mutate(root, info, code):
        from apps.cart.models import Cart
        from .models import CouponRedemption

        user = info.context.user
        try:
            coupon = Coupon.objects.get(code__iexact=code.strip())
        except Coupon.DoesNotExist:
            return ValidateCoupon(ok=False, error="Invalid coupon code.")

        if not coupon.is_valid_now():
            return ValidateCoupon(ok=False, error="This coupon is expired or no longer active.")

        redemptions_by_user = CouponRedemption.objects.filter(coupon=coupon, user=user).count()
        if redemptions_by_user >= coupon.usage_limit_per_user:
            return ValidateCoupon(ok=False, error="You have already used this coupon.")

        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            return ValidateCoupon(ok=False, error="Your cart is empty.")

        subtotal = cart.subtotal
        if subtotal < coupon.min_order_value:
            return ValidateCoupon(
                ok=False,
                error=f"This coupon requires a minimum order value of {coupon.min_order_value}.",
            )

        discount = coupon.calculate_discount(subtotal)
        return ValidateCoupon(ok=True, discount_amount=discount)


class CouponInput(graphene.InputObjectType):
    code = graphene.String(required=True)
    description = graphene.String()
    discount_type = graphene.String(required=True)
    discount_value = graphene.Decimal(required=True)
    max_discount_amount = graphene.Decimal()
    min_order_value = graphene.Decimal()
    valid_from = graphene.DateTime()
    valid_until = graphene.DateTime(required=True)
    usage_limit_total = graphene.Int()
    usage_limit_per_user = graphene.Int()
    is_active = graphene.Boolean()


class UpsertCoupon(graphene.Mutation):
    class Arguments:
        id = graphene.ID()
        input = CouponInput(required=True)

    ok = graphene.Boolean()
    coupon = graphene.Field(CouponType)

    @admin_required
    def mutate(root, info, input, id=None):
        data = {k: v for k, v in input.items() if v is not None}
        data["code"] = data["code"].strip().upper()

        if id:
            coupon = Coupon.objects.get(id=id)
            for k, v in data.items():
                setattr(coupon, k, v)
        else:
            coupon = Coupon(**data)

        coupon.full_clean()
        coupon.save()
        return UpsertCoupon(ok=True, coupon=coupon)


class DeactivateCoupon(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @admin_required
    def mutate(root, info, id):
        updated = Coupon.objects.filter(id=id).update(is_active=False)
        if not updated:
            raise GraphQLError("Coupon not found.")
        return DeactivateCoupon(ok=True)


class CouponsQuery(graphene.ObjectType):
    coupons = graphene.List(CouponType)

    @admin_required
    def resolve_coupons(root, info):
        return Coupon.objects.all().order_by("-created_at")


class CouponsMutation(graphene.ObjectType):
    validate_coupon = ValidateCoupon.Field()
    upsert_coupon = UpsertCoupon.Field()
    deactivate_coupon = DeactivateCoupon.Field()
