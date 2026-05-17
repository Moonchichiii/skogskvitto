from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db.models import QuerySet

from apps.scanning.models import ReceiptScanJob


def get_user_scan_job(
    user: AbstractBaseUser | AnonymousUser, job_id: int
) -> ReceiptScanJob | None:
    if not user.is_authenticated or user.pk is None:
        return None

    return ReceiptScanJob.objects.filter(pk=job_id, user_id=user.pk).first()


def list_active_scan_jobs(
    user: AbstractBaseUser | AnonymousUser,
) -> QuerySet[ReceiptScanJob]:
    if not user.is_authenticated or user.pk is None:
        return ReceiptScanJob.objects.none()

    return ReceiptScanJob.objects.filter(
        user_id=user.pk,
        status__in=[
            ReceiptScanJob.Status.PENDING,
            ReceiptScanJob.Status.QUEUED,
            ReceiptScanJob.Status.PROCESSING,
            ReceiptScanJob.Status.REVIEW_READY,
        ],
    ).order_by("-created_at")
