from __future__ import annotations

from django.contrib import admin

from apps.receipts.models import Receipt, TaxYear


@admin.register(TaxYear)
class TaxYearAdmin(admin.ModelAdmin):
    list_display = ("year", "owner", "status", "locked_at", "created_at")
    list_filter = ("status", "year")
    search_fields = ("owner__email",)
    readonly_fields = ("created_at", "updated_at", "locked_at")
    ordering = ("-year",)


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "vendor",
        "owner",
        "tax_year",
        "total_amount",
        "vat_amount",
        "net_amount",
    )
    list_filter = ("tax_year__year", "category")
    search_fields = ("vendor", "note", "owner__email")
    readonly_fields = ("created_at", "updated_at", "tax_year", "net_amount")
    date_hierarchy = "date"
    ordering = ("-date",)

