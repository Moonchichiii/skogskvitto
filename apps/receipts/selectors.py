from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db.models import Count, QuerySet, Sum

from apps.receipts.models import Receipt, TaxYear


def user_receipts(user: AbstractBaseUser | AnonymousUser) -> QuerySet[Receipt]:
    if not user.is_authenticated or user.pk is None:
        return Receipt.objects.none()
    return Receipt.objects.filter(owner_id=user.pk)


def user_tax_years(user: AbstractBaseUser | AnonymousUser) -> QuerySet[TaxYear]:
    if not user.is_authenticated or user.pk is None:
        return TaxYear.objects.none()
    return TaxYear.objects.filter(owner_id=user.pk)


def tax_years_with_totals(
    user: AbstractBaseUser | AnonymousUser,
) -> QuerySet[TaxYear]:
    """All TaxYears for the user, annotated with receipt count and totals."""
    return (
        user_tax_years(user)
        .annotate(
            receipt_count=Count("receipts"),
            total_sum=Sum("receipts__total_amount"),
            vat_sum=Sum("receipts__vat_amount"),
        )
        .order_by("-year")
    )


def receipts_for_year(
    user: AbstractBaseUser | AnonymousUser, year: int
) -> QuerySet[Receipt]:
    return user_receipts(user).filter(date__year=year).order_by("-date", "-created_at")


def year_totals(
    user: AbstractBaseUser | AnonymousUser, year: int
) -> dict[str, Decimal | int]:
    aggregates = user_receipts(user).filter(date__year=year).aggregate(
        total=Sum("total_amount"),
        vat=Sum("vat_amount"),
        count=Count("id"),
    )
    return {
        "total": aggregates.get("total") or Decimal("0.00"),
        "vat": aggregates.get("vat") or Decimal("0.00"),
        "count": aggregates.get("count") or 0,
    }


def latest_receipts(
    user: AbstractBaseUser | AnonymousUser, limit: int = 20
) -> list[Receipt]:
    return list(user_receipts(user).order_by("-created_at")[:limit])


def current_year() -> int:
    return date_type.today().year
