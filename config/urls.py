from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView

from apps.billing.views import billing_cancel, billing_success, start_checkout
from apps.core.views import dashboard, home
from apps.exports.views import export_excel
from apps.receipts.views import (
    receipts_list,
    tax_year_detail,
    tax_year_list,
    tax_year_lock,
    tax_year_unlock,
)

urlpatterns = [
    path("", home, name="home"),
    path(
        "favicon.ico",
        RedirectView.as_view(url="/static/img/favicon.svg", permanent=True),
    ),
    path("", include("apps.accounts.urls")),
    path("", include("apps.scanning.urls")),

    # Authenticated overview
    path("dashboard/", dashboard, name="dashboard"),

    # Receipts collection
    path("kvitton/", receipts_list, name="receipts_list"),

    # Tax years
    path("inkomstar/", tax_year_list, name="tax_year_list"),
    path("inkomstar/<int:year>/", tax_year_detail, name="tax_year_detail"),
    path("inkomstar/<int:year>/las/", tax_year_lock, name="tax_year_lock"),
    path("inkomstar/<int:year>/las-upp/", tax_year_unlock, name="tax_year_unlock"),

    # Export
    path("receipts/export/excel/", export_excel, name="export_excel"),

    # Legal
    path(
        "integritetspolicy/",
        TemplateView.as_view(template_name="core/legal/privacy_policy.html"),
        name="privacy_policy",
    ),
    path(
        "anvandarvillkor/",
        TemplateView.as_view(template_name="core/legal/terms_of_service.html"),
        name="terms_of_service",
    ),
    path(
        "cookies/",
        TemplateView.as_view(template_name="core/legal/cookies.html"),
        name="cookies",
    ),

    # Billing
    path("billing/checkout/", start_checkout, name="start_checkout"),
    path("billing/success/", billing_success, name="billing_success"),
    path("billing/cancel/", billing_cancel, name="billing_cancel"),

    # Auth (allauth)
    path("accounts/", include("allauth.urls")),

    # Django RQ (admin interface for background jobs)
    path("django-rq/", include("django_rq.urls")),

    # Admin
    path("admin/", admin.site.urls),
]
