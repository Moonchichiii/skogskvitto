from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView
from ninja import NinjaAPI

from apps.accounts.views import profile
from apps.billing.views import billing_cancel, billing_success, start_checkout
from apps.core.views import home
from apps.exports.views import export_excel
from apps.receipts.api import router as receipts_router
from apps.receipts.views import dashboard, scan

api = NinjaAPI()
api.add_router("receipts/", receipts_router)

urlpatterns = [
    path("", home, name="home"),
    path("favicon.ico", RedirectView.as_view(url="/static/img/favicon.svg", permanent=True)),
    path("scan/", scan, name="scan"),
    path("dashboard/", dashboard, name="dashboard"),
    path("profile/", profile, name="profile"),
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
    path("receipts/export/excel/", export_excel, name="export_excel"),
    path("billing/checkout/", start_checkout, name="start_checkout"),
    path("billing/success/", billing_success, name="billing_success"),
    path("billing/cancel/", billing_cancel, name="billing_cancel"),
    path("accounts/", include("allauth.urls")),
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
