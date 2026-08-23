from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Address, EmailVerificationToken, PasswordResetToken, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-created_at"]
    list_display = ["email", "full_name", "role", "is_active", "is_email_verified", "created_at"]
    list_filter = ["role", "is_active", "is_email_verified"]
    search_fields = ["email", "first_name", "last_name", "phone_number"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "phone_number")}),
        ("Role & permissions", {
            "fields": ("role", "is_active", "is_staff", "is_superuser", "is_email_verified", "groups", "user_permissions")
        }),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2", "role")}),
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["user", "label", "city", "state", "is_default"]
    list_filter = ["label", "is_default", "state"]
    search_fields = ["user__email", "city", "postal_code"]


admin.site.register(EmailVerificationToken)
admin.site.register(PasswordResetToken)
