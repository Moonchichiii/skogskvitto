from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from ninja import NinjaAPI

from apps.core.views import index
from apps.receipts.api import router as receipts_router
from apps.receipts.views import (
    billing_cancel,
    billing_success,
    dashboard,
    export_excel,
    start_checkout,
)

api = NinjaAPI()
api.add_router("receipts/", receipts_router)

urlpatterns = [
    path("", index, name="index"),
    path("dashboard/", dashboard, name="dashboard"),
    path(
        "integritetspolicy/",
        TemplateView.as_view(template_name="core/privacy_policy.html"),
        name="privacy_policy",
    ),
    path(
        "anvandarvillkor/",
        TemplateView.as_view(template_name="core/terms_of_service.html"),
        name="terms_of_service",
    ),
    path("receipts/export/excel/", export_excel, name="export_excel"),
    path("billing/checkout/", start_checkout, name="start_checkout"),
    path("billing/success/", billing_success, name="billing_success"),
    path("billing/cancel/", billing_cancel, name="billing_cancel"),
    path("accounts/", include("allauth.urls")),
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
