import enum

from django.db import models


class TimeStampedModel(models.Model):
    """Adds created/updated timestamps. Inherit this in every domain model."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        # Django TextChoices fields keep their Enum-member type in memory
        # until a fresh DB round-trip normalizes them to a plain str. If a
        # mutation returns `self` in the same request (e.g. right after
        # Order.objects.create() or a status transition), graphene-django's
        # auto-generated Enum type fails to serialize that Enum-typed value
        # even though it's string-identical to a valid choice. Coercing to
        # `str(value)` here (which TextChoices defines as the plain value)
        # keeps every choices field GraphQL-safe with zero extra DB queries.
        for field in self._meta.fields:
            if getattr(field, "choices", None):
                value = getattr(self, field.attname, None)
                if isinstance(value, enum.Enum):
                    setattr(self, field.attname, str(value))
        super().save(*args, **kwargs)


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(is_deleted=False)

    def dead(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    """
    Products/Categories are soft-deleted rather than hard-deleted so historical
    orders retain valid references even after a product is discontinued.
    """

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self):
        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])
