import base64

import graphene
from django.db.models import Q
from graphene_django import DjangoObjectType
from graphql import GraphQLError

from apps.core.permissions import admin_required
from .models import Brand, Category, Product, ProductImage


class CategoryType(DjangoObjectType):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "children", "description", "is_active"]
        # Deliberately NOT a Relay Node: this app's GraphQL contract treats
        # `id` as the raw integer primary key everywhere (mutations accept
        # it straight back as an Int argument). Implementing relay.Node here
        # would silently replace `id` with an opaque base64 string instead,
        # breaking every mutation that round-trips an id from a query.


class BrandType(DjangoObjectType):
    class Meta:
        model = Brand
        fields = ["id", "name", "slug", "logo", "description", "is_active"]
        # See CategoryType note above — no relay.Node here either.


class ProductImageType(DjangoObjectType):
    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt_text", "display_order", "is_primary"]


class ProductSortEnum(graphene.Enum):
    PRICE_LOW_TO_HIGH = "price"
    PRICE_HIGH_TO_LOW = "-price"
    NEWEST = "-created_at"
    BEST_SELLING = "-units_sold"


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = [
            "id", "sku", "name", "slug", "description", "category", "brand",
            "manufacturer_name", "manufacturer_address", "price", "compare_at_price",
            "specifications", "safety_information", "storage_instructions",
            "availability_status", "images", "related_products", "average_rating",
            "units_sold", "created_at",
        ]
        # No relay.Node — see CategoryType note above. `id` is the raw
        # integer primary key; every mutation that takes a product id back
        # as an argument (addToCart, addToWishlist, uploadProductImage,
        # upsertProduct, ...) uses a plain Int argument.

    stock_quantity = graphene.Int()

    def resolve_stock_quantity(self, info):
        from apps.inventory.models import StockRecord

        # Sum sellable (available - reserved) quantity across all batches.
        records = StockRecord.objects.filter(batch__product=self).select_related("batch")
        return sum(r.sellable_quantity for r in records)


# ---------------------------------------------------------------------------
# Manual, non-Relay pagination for `products`.
#
# The frontend expects a Relay-*shaped* response ({ pageInfo { hasNextPage
# endCursor } edges { node { ... } } }) for its "load more" flow, but we
# deliberately do NOT use DjangoFilterConnectionField/relay.Node to get it,
# since that's what coupled `id` to Relay's opaque global-id encoding in the
# first place. This hand-rolled version produces the identical response
# shape the frontend already queries, using plain integer-offset cursors
# instead, with zero effect on how `id` is represented anywhere.
# ---------------------------------------------------------------------------
class PageInfoType(graphene.ObjectType):
    has_next_page = graphene.Boolean()
    end_cursor = graphene.String()


class ProductEdgeType(graphene.ObjectType):
    node = graphene.Field(ProductType)
    cursor = graphene.String()


class ProductConnectionType(graphene.ObjectType):
    edges = graphene.List(ProductEdgeType)
    page_info = graphene.Field(PageInfoType)


def _encode_cursor(offset: int) -> str:
    return base64.b64encode(f"offset:{offset}".encode()).decode()


def _decode_cursor(cursor: str) -> int:
    try:
        raw = base64.b64decode(cursor).decode()
        return int(raw.split(":", 1)[1])
    except Exception:
        return -1


class CatalogQuery(graphene.ObjectType):
    categories = graphene.List(CategoryType, active_only=graphene.Boolean(default_value=True))
    brands = graphene.List(BrandType, active_only=graphene.Boolean(default_value=True))
    product = graphene.Field(ProductType, slug=graphene.String(required=True))
    products = graphene.Field(
        ProductConnectionType,
        first=graphene.Int(),
        after=graphene.String(),
        category=graphene.String(),
        brand=graphene.String(),
        min_price=graphene.Decimal(),
        max_price=graphene.Decimal(),
        in_stock_only=graphene.Boolean(),
        search=graphene.String(),
        sort=ProductSortEnum(),
    )

    def resolve_categories(root, info, active_only):
        qs = Category.objects.filter(parent__isnull=True)
        if active_only:
            qs = qs.filter(is_active=True)
        return qs

    def resolve_brands(root, info, active_only):
        qs = Brand.objects.all()
        if active_only:
            qs = qs.filter(is_active=True)
        return qs

    def resolve_product(root, info, slug):
        try:
            return Product.objects.select_related("category", "brand").prefetch_related("images").get(
                slug=slug, is_active=True
            )
        except Product.DoesNotExist:
            raise GraphQLError("Product not found.")

    def resolve_products(
        root, info, first=None, after=None, category=None, brand=None,
        min_price=None, max_price=None, in_stock_only=None, search=None, sort=None,
    ):
        qs = Product.objects.filter(is_active=True).select_related("category", "brand")

        if category:
            qs = qs.filter(category__slug=category)
        if brand:
            qs = qs.filter(brand__slug=brand)
        if min_price is not None:
            qs = qs.filter(price__gte=min_price)
        if max_price is not None:
            qs = qs.filter(price__lte=max_price)
        if in_stock_only:
            qs = qs.filter(availability_status=Product.AvailabilityStatus.IN_STOCK)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search) | Q(sku__iexact=search))

        # Explicit, stable ordering is required for offset-based pagination
        # to give consistent results across pages.
        qs = qs.order_by(sort, "id") if sort else qs.order_by("-created_at", "id")

        limit = first or 12
        offset = _decode_cursor(after) + 1 if after else 0

        # Fetch one extra row to know whether there's a next page.
        page = list(qs[offset: offset + limit + 1])
        has_next = len(page) > limit
        page = page[:limit]

        edges = [
            ProductEdgeType(node=item, cursor=_encode_cursor(offset + idx))
            for idx, item in enumerate(page)
        ]
        end_cursor = edges[-1].cursor if edges else None

        return ProductConnectionType(
            edges=edges,
            page_info=PageInfoType(has_next_page=has_next, end_cursor=end_cursor),
        )


# ---------------------------------------------------------------------------
# Admin CRUD mutations (Category / Brand / Product)
# ---------------------------------------------------------------------------
class CategoryInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    parent_id = graphene.ID()
    description = graphene.String()
    is_active = graphene.Boolean()


class UpsertCategory(graphene.Mutation):
    class Arguments:
        id = graphene.ID()
        input = CategoryInput(required=True)

    ok = graphene.Boolean()
    category = graphene.Field(CategoryType)

    @admin_required
    def mutate(root, info, input, id=None):
        parent = None
        if input.get("parent_id"):
            parent = Category.objects.get(id=input["parent_id"])

        defaults = {
            "name": input["name"],
            "parent": parent,
            "description": input.get("description", ""),
            "is_active": input.get("is_active", True),
        }
        if id:
            category = Category.objects.get(id=id)
            for k, v in defaults.items():
                setattr(category, k, v)
            category.save()
        else:
            category = Category.objects.create(**defaults)
        return UpsertCategory(ok=True, category=category)


class DeleteCategory(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @admin_required
    def mutate(root, info, id):
        category = Category.objects.get(id=id)
        category.soft_delete()
        return DeleteCategory(ok=True)


class BrandInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    description = graphene.String()
    is_active = graphene.Boolean()


class UpsertBrand(graphene.Mutation):
    class Arguments:
        id = graphene.ID()
        input = BrandInput(required=True)

    ok = graphene.Boolean()
    brand = graphene.Field(BrandType)

    @admin_required
    def mutate(root, info, input, id=None):
        defaults = {
            "name": input["name"],
            "description": input.get("description", ""),
            "is_active": input.get("is_active", True),
        }
        if id:
            brand = Brand.objects.get(id=id)
            for k, v in defaults.items():
                setattr(brand, k, v)
            brand.save()
        else:
            brand = Brand.objects.create(**defaults)
        return UpsertBrand(ok=True, brand=brand)


class ProductInput(graphene.InputObjectType):
    sku = graphene.String(required=True)
    name = graphene.String(required=True)
    description = graphene.String(required=True)
    category_id = graphene.ID(required=True)
    brand_id = graphene.ID(required=True)
    manufacturer_name = graphene.String(required=True)
    manufacturer_address = graphene.String()
    price = graphene.Decimal(required=True)
    compare_at_price = graphene.Decimal()
    specifications = graphene.JSONString()
    safety_information = graphene.String()
    storage_instructions = graphene.String()
    is_active = graphene.Boolean()


class UpsertProduct(graphene.Mutation):
    """Multi-image upload is handled by a separate UploadProductImage mutation
    (multipart upload) so this mutation stays simple JSON in/out."""

    class Arguments:
        id = graphene.ID()
        input = ProductInput(required=True)

    ok = graphene.Boolean()
    product = graphene.Field(ProductType)

    @admin_required
    def mutate(root, info, input, id=None):
        category = Category.objects.get(id=input["category_id"])
        brand = Brand.objects.get(id=input["brand_id"])

        defaults = dict(input)
        defaults["category"] = category
        defaults["brand"] = brand
        defaults.pop("category_id")
        defaults.pop("brand_id")

        if id:
            product = Product.objects.get(id=id)
            for k, v in defaults.items():
                if v is not None:
                    setattr(product, k, v)
            product.save()
        else:
            product = Product.objects.create(**{k: v for k, v in defaults.items() if v is not None})
        return UpsertProduct(ok=True, product=product)


class DeleteProduct(graphene.Mutation):
    class Arguments:
        id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @admin_required
    def mutate(root, info, id):
        product = Product.objects.get(id=id)
        product.soft_delete()
        return DeleteProduct(ok=True)


from graphene_file_upload.scalars import Upload


class UploadProductImage(graphene.Mutation):
    class Arguments:
        product_id = graphene.ID(required=True)
        # Must be the Upload scalar, not String: graphene-file-upload
        # substitutes the real uploaded file object into this variable
        # before GraphQL validates/executes the request (per the
        # graphql-multipart-request-spec). A String-typed argument rejects
        # that file object at validation time ("String cannot represent a
        # non string value"), before the resolver ever runs.
        image = Upload(required=True)
        alt_text = graphene.String()
        is_primary = graphene.Boolean()

    ok = graphene.Boolean()
    image = graphene.Field(ProductImageType)

    @admin_required
    def mutate(root, info, product_id, image, alt_text="", is_primary=False):
        # With the Upload scalar, `image` IS the uploaded file object itself
        # (an UploadedFile instance) — no need to look anything up in
        # request.FILES.
        product = Product.objects.get(id=product_id)
        img = ProductImage.objects.create(
            product=product, image=image, alt_text=alt_text, is_primary=is_primary
        )
        return UploadProductImage(ok=True, image=img)


class CatalogMutation(graphene.ObjectType):
    upsert_category = UpsertCategory.Field()
    delete_category = DeleteCategory.Field()
    upsert_brand = UpsertBrand.Field()
    upsert_product = UpsertProduct.Field()
    delete_product = DeleteProduct.Field()
    upload_product_image = UploadProductImage.Field()
