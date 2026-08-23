import graphene
from graphene_django import DjangoObjectType
from graphql import GraphQLError

from apps.catalog.models import Product
from apps.core.permissions import login_required
from .models import Cart, CartItem, Wishlist, WishlistItem


class CartItemType(DjangoObjectType):
    class Meta:
        model = CartItem
        fields = ["id", "product", "quantity", "unit_price_snapshot"]

    line_total = graphene.Decimal()

    def resolve_line_total(self, info):
        return self.line_total


class CartType(DjangoObjectType):
    class Meta:
        model = Cart
        fields = ["id", "items", "updated_at"]

    subtotal = graphene.Decimal()

    def resolve_subtotal(self, info):
        return self.subtotal


class WishlistItemType(DjangoObjectType):
    class Meta:
        model = WishlistItem
        fields = ["id", "product", "created_at"]


class WishlistType(DjangoObjectType):
    class Meta:
        model = Wishlist
        fields = ["id", "items"]


def _get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def _get_or_create_wishlist(user):
    wishlist, _ = Wishlist.objects.get_or_create(user=user)
    return wishlist


class CartQuery(graphene.ObjectType):
    my_cart = graphene.Field(CartType)
    my_wishlist = graphene.Field(WishlistType)

    @login_required
    def resolve_my_cart(root, info):
        return _get_or_create_cart(info.context.user)

    @login_required
    def resolve_my_wishlist(root, info):
        return _get_or_create_wishlist(info.context.user)


class AddToCart(graphene.Mutation):
    class Arguments:
        product_id = graphene.ID(required=True)
        quantity = graphene.Int(default_value=1)

    ok = graphene.Boolean()
    cart = graphene.Field(CartType)

    @login_required
    def mutate(root, info, product_id, quantity):
        if quantity < 1:
            raise GraphQLError("Quantity must be at least 1.")

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            raise GraphQLError("Product not found.")

        if product.availability_status != Product.AvailabilityStatus.IN_STOCK:
            raise GraphQLError("This product is currently out of stock.")

        cart = _get_or_create_cart(info.context.user)
        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={"quantity": quantity, "unit_price_snapshot": product.price},
        )
        if not created:
            item.quantity += quantity
            item.unit_price_snapshot = product.price
            item.save()

        return AddToCart(ok=True, cart=cart)


class UpdateCartItem(graphene.Mutation):
    class Arguments:
        item_id = graphene.ID(required=True)
        quantity = graphene.Int(required=True)

    ok = graphene.Boolean()
    cart = graphene.Field(CartType)

    @login_required
    def mutate(root, info, item_id, quantity):
        try:
            item = CartItem.objects.get(id=item_id, cart__user=info.context.user)
        except CartItem.DoesNotExist:
            raise GraphQLError("Cart item not found.")

        if quantity < 1:
            item.delete()
        else:
            item.quantity = quantity
            item.save()

        return UpdateCartItem(ok=True, cart=_get_or_create_cart(info.context.user))


class RemoveFromCart(graphene.Mutation):
    class Arguments:
        item_id = graphene.ID(required=True)

    ok = graphene.Boolean()
    cart = graphene.Field(CartType)

    @login_required
    def mutate(root, info, item_id):
        deleted, _ = CartItem.objects.filter(id=item_id, cart__user=info.context.user).delete()
        if not deleted:
            raise GraphQLError("Cart item not found.")
        return RemoveFromCart(ok=True, cart=_get_or_create_cart(info.context.user))


class AddToWishlist(graphene.Mutation):
    class Arguments:
        product_id = graphene.ID(required=True)

    ok = graphene.Boolean()
    wishlist = graphene.Field(WishlistType)

    @login_required
    def mutate(root, info, product_id):
        product = Product.objects.get(id=product_id)
        wishlist = _get_or_create_wishlist(info.context.user)
        WishlistItem.objects.get_or_create(wishlist=wishlist, product=product)
        return AddToWishlist(ok=True, wishlist=wishlist)


class RemoveFromWishlist(graphene.Mutation):
    class Arguments:
        product_id = graphene.ID(required=True)

    ok = graphene.Boolean()
    wishlist = graphene.Field(WishlistType)

    @login_required
    def mutate(root, info, product_id):
        wishlist = _get_or_create_wishlist(info.context.user)
        WishlistItem.objects.filter(wishlist=wishlist, product_id=product_id).delete()
        return RemoveFromWishlist(ok=True, wishlist=wishlist)


class MoveWishlistItemToCart(graphene.Mutation):
    """One-click move: adds to cart, removes from wishlist, atomically."""

    class Arguments:
        product_id = graphene.ID(required=True)
        quantity = graphene.Int(default_value=1)

    ok = graphene.Boolean()
    cart = graphene.Field(CartType)
    wishlist = graphene.Field(WishlistType)

    @login_required
    def mutate(root, info, product_id, quantity):
        from django.db import transaction

        user = info.context.user
        product = Product.objects.get(id=product_id, is_active=True)

        with transaction.atomic():
            cart = _get_or_create_cart(user)
            item, created = CartItem.objects.get_or_create(
                cart=cart, product=product,
                defaults={"quantity": quantity, "unit_price_snapshot": product.price},
            )
            if not created:
                item.quantity += quantity
                item.save()

            wishlist = _get_or_create_wishlist(user)
            WishlistItem.objects.filter(wishlist=wishlist, product=product).delete()

        return MoveWishlistItemToCart(ok=True, cart=cart, wishlist=wishlist)


class CartMutation(graphene.ObjectType):
    add_to_cart = AddToCart.Field()
    update_cart_item = UpdateCartItem.Field()
    remove_from_cart = RemoveFromCart.Field()
    add_to_wishlist = AddToWishlist.Field()
    remove_from_wishlist = RemoveFromWishlist.Field()
    move_wishlist_item_to_cart = MoveWishlistItemToCart.Field()
