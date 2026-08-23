import secrets

from django.db import models
from django.utils.text import slugify

from apps.core.models import SoftDeleteModel, TimeStampedModel
from apps.core.validators import product_image_upload_path, validate_image_file


class Category(TimeStampedModel, SoftDeleteModel):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "categories"
        verbose_name_plural = "categories"
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["is_active"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(TimeStampedModel, SoftDeleteModel):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    logo = models.ImageField(upload_to="brands/", null=True, blank=True, validators=[validate_image_file])
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "brands"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(TimeStampedModel, SoftDeleteModel):
    """
    Core catalog item. Stock quantities themselves live in
    apps.inventory (StockBatch) so that batch/expiry tracking is
    normalized separately from the product record.
    """

    class AvailabilityStatus(models.TextChoices):
        IN_STOCK = "IN_STOCK", "In Stock"
        OUT_OF_STOCK = "OUT_OF_STOCK", "Out of Stock"
        DISCONTINUED = "DISCONTINUED", "Discontinued"

    sku = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products")

    manufacturer_name = models.CharField(max_length=255)
    manufacturer_address = models.TextField(blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Original/MRP price used to show a strikethrough discount.",
    )

    # Free-form structured spec fields, e.g. {"Composition": "...", "Dosage form": "Tablet"}
    specifications = models.JSONField(default=dict, blank=True)

    safety_information = models.TextField(blank=True)
    storage_instructions = models.TextField(blank=True)

    availability_status = models.CharField(
        max_length=20, choices=AvailabilityStatus.choices, default=AvailabilityStatus.IN_STOCK
    )

    is_active = models.BooleanField(default=True)
    related_products = models.ManyToManyField("self", blank=True, symmetrical=True)

    # Denormalized counters, updated by signals/celery for fast sort queries
    units_sold = models.PositiveIntegerField(default=0, db_index=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)

    class Meta:
        db_table = "products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["availability_status"]),
            models.Index(fields=["price"]),
            models.Index(fields=["-units_sold"]),
            models.Index(fields=["category", "brand"]),
        ]

    def save(self, *args, **kwargs):
        # NOTE: with an auto-increment PK, self.id doesn't exist yet before
        # the first save (the DB assigns it on insert), unlike the old
        # client-side UUID default. A random suffix keeps the slug unique
        # without depending on a pre-save id.
        if not self.slug:
            self.slug = slugify(self.name)[:270] + "-" + secrets.token_hex(4)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=product_image_upload_path, validators=[validate_image_file])
    alt_text = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "product_images"
        ordering = ["display_order"]

    def save(self, *args, **kwargs):
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).exclude(pk=self.pk).update(
                is_primary=False
            )
        super().save(*args, **kwargs)


class ProductBatch(TimeStampedModel):
    """
    Expiration date is tracked per manufacturing batch (a product can have
    several batches in stock at once with different expiry dates); this
    also backs apps.inventory's stock ledger via a FK.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="batches")
    batch_number = models.CharField(max_length=100)
    expiration_date = models.DateField()
    manufactured_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "product_batches"
        unique_together = ("product", "batch_number")
        indexes = [models.Index(fields=["expiration_date"])]

    def __str__(self):
        return f"{self.product.name} - batch {self.batch_number}"
