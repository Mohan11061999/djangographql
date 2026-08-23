from django.contrib import admin

from .models import Brand, Category, Product, ProductBatch, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductBatchInline(admin.TabularInline):
    model = ProductBatch
    extra = 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "is_active"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "sku", "category", "brand", "price", "availability_status", "is_active"]
    list_filter = ["category", "brand", "availability_status", "is_active"]
    search_fields = ["name", "sku"]
    inlines = [ProductImageInline, ProductBatchInline]
    prepopulated_fields = {"slug": ("name",)}
