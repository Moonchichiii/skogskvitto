from django.contrib import admin

from apps.properties.models import Property


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_default", "slug", "created_at")
    list_filter = ("is_default",)
    search_fields = ("name", "slug", "owner__email")
    readonly_fields = ("slug", "created_at", "updated_at")
    ordering = ("-is_default", "name")
