from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView

from apps.billing.views import billing_cancel, billing_success, start_checkout
from apps.core.views import dashboard, home
from apps.exports.views import export_excel

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

    # Receipts + Tax Years (kvitton/, inkomstar/, including detail/edit/delete)
    path("", include("apps.receipts.urls")),

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
