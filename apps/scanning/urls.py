from django.urls import path

from apps.scanning.views import scan

urlpatterns = [
    path("scan/", scan, name="scan"),
]
