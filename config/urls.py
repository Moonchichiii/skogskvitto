from typing import Any, cast

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
    path("", cast(Any, index), name="index"),
    path("dashboard/", cast(Any, dashboard), name="dashboard"),
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
    path(
        "cookies/",
        TemplateView.as_view(template_name="core/cookies.html"),
        name="cookies",
    ),
    path("receipts/export/excel/", cast(Any, export_excel), name="export_excel"),
    path("billing/checkout/", cast(Any, start_checkout), name="start_checkout"),
    path("billing/success/", cast(Any, billing_success), name="billing_success"),
    path("billing/cancel/", cast(Any, billing_cancel), name="billing_cancel"),
    path("accounts/", include("allauth.urls")),
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
