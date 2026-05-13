from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from core.views import index
from receipts.api import router as receipts_router

api = NinjaAPI()
api.add_router("receipts/", receipts_router)

urlpatterns = [
    path("", index, name="index"),
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
