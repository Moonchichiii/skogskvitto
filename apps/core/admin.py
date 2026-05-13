from typing import Any

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpRequest

from apps.core.models import User


@admin.register(User)
class SkogsKvittoUserAdmin(UserAdmin):  # type: ignore[type-arg]
    list_display = (*UserAdmin.list_display, "is_pilot")  # type: ignore[misc]
    list_filter = (*UserAdmin.list_filter, "is_pilot")

    def get_fieldsets(
        self,
        request: HttpRequest,
        obj: User | None = None,
    ) -> Any:
        fieldsets = list(super().get_fieldsets(request, obj))
        fieldsets.append(("SkogsKvitto", {"fields": ("is_pilot",)}))
        return fieldsets
