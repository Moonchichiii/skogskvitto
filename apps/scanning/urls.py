from django.urls import path

from apps.scanning.views import confirm, intake, scan, sign_upload, status

urlpatterns = [
    path("scan/", scan, name="scan"),
    path("scanning/sign/", sign_upload, name="scanning_sign"),
    path("scanning/job/<int:job_id>/intake/", intake, name="scanning_intake"),
    path("scanning/job/<int:job_id>/status/", status, name="scanning_status"),
    path("scanning/job/<int:job_id>/confirm/", confirm, name="scanning_confirm"),
]
