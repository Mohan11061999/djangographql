from django.contrib import admin

from .models import EmailLog


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ["email_type", "recipient", "was_successful", "created_at"]
    list_filter = ["email_type", "was_successful"]
    search_fields = ["recipient"]
    readonly_fields = [f.name for f in EmailLog._meta.fields]
