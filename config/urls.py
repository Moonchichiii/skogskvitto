from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from core.views import index

api = NinjaAPI()

urlpatterns = [
    path("", index, name="index"),
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
