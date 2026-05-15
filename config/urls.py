from typing import Any, cast

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView
from ninja import NinjaAPI

from apps.core.views import profile
from apps.receipts.api import router as receipts_router
from apps.receipts.views import (
    billing_cancel,
    billing_success,
    dashboard,
    export_excel,
    scan,
    start_checkout,
)

api = NinjaAPI()
api.add_router("receipts/", receipts_router)

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="scan", permanent=False), name="home"),
    path("scan/", cast(Any, scan), name="scan"),
    path("dashboard/", cast(Any, dashboard), name="dashboard"),
    path("profile/", cast(Any, profile), name="profile"),
    path(
        "integritetspolicy/",
        TemplateView.as_view(template_name="legal/privacy_policy.html"),
        name="privacy_policy",
    ),
    path(
        "anvandarvillkor/",
        TemplateView.as_view(template_name="legal/terms_of_service.html"),
        name="terms_of_service",
    ),
    path(
        "cookies/",
        TemplateView.as_view(template_name="legal/cookies.html"),
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
