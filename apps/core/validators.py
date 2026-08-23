import os
import re
import secrets

from django.conf import settings
from django.core.exceptions import ValidationError


def validate_image_file(file):
    """Validates extension and size for any uploaded product/category image."""
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in settings.ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type '{ext}'. Allowed: {', '.join(settings.ALLOWED_IMAGE_EXTENSIONS)}"
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(f"File too large. Max size is {settings.MAX_UPLOAD_SIZE_MB}MB.")


def sanitize_filename(filename: str) -> str:
    """
    Strips path separators and unsafe characters, and appends a random
    suffix so two uploads with the same original name never collide on disk.
    """
    ext = os.path.splitext(filename)[1].lower()
    base = os.path.splitext(filename)[0]
    base = re.sub(r"[^a-zA-Z0-9_-]", "-", base)[:60]
    return f"{base}-{secrets.token_hex(4)}{ext}"


def product_image_upload_path(instance, filename):
    """
    Stores under /media/products/product_<id>/<sanitized-filename>
    as required by the spec. `instance` is a ProductImage row.
    """
    safe_name = sanitize_filename(filename)
    product_id = instance.product_id or "unsaved"
    return f"products/product_{product_id}/{safe_name}"
