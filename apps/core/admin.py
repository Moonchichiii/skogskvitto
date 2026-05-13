from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.core.models import User


@admin.register(User)
class SkogsKvittoUserAdmin(UserAdmin):
    list_display = (*UserAdmin.list_display, "is_pilot")
    list_filter = (*UserAdmin.list_filter, "is_pilot")
    fieldsets = (
        *UserAdmin.fieldsets,
        ("SkogsKvitto", {"fields": ("is_pilot",)}),
    )
