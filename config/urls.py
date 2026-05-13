from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from apps.core.views import index
from apps.receipts.api import router as receipts_router
from apps.receipts.views import dashboard, export_excel

api = NinjaAPI()
api.add_router("receipts/", receipts_router)

urlpatterns = [
    path("", index, name="index"),
    path("dashboard/", dashboard, name="dashboard"),
    path("receipts/export/excel/", export_excel, name="export_excel"),
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
