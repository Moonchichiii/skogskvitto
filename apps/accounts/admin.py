from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.forms import UserChangeForm, UserCreationForm
from apps.accounts.models import User


@admin.register(User)
class SkogsKvittoUserAdmin(UserAdmin):
    model = User
    form = UserChangeForm
    add_form = UserCreationForm

    ordering = ("email",)
    search_fields = ("email", "first_name", "last_name")

    list_display = (
        "email",
        "is_active",
        "is_staff",
        "is_superuser",
        "is_pilot",
        "date_joined",
    )

    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "is_pilot",
        "groups",
    )

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personuppgifter", {"fields": ("first_name", "last_name")}),
        ("SkogsKvitto", {"fields": ("is_pilot",)}),
        (
            "Behörigheter",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Viktiga datum", {"fields": ("last_login", "date_joined")}),
    )

    readonly_fields = ("last_login", "date_joined")

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_pilot",
                ),
            },
        ),
    )
