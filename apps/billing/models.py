from __future__ import annotations

from django.conf import settings
from django.db import models


class UserSubscription(models.Model):
    """A user's Stripe subscription state.

    Owned by the billing app. Mirrors the most recent webhook state from
    Stripe so feature gating can be evaluated without a round-trip.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        TRIALING = "trialing", "Trialing"
        CANCELED = "canceled", "Canceled"
        INCOMPLETE = "incomplete", "Incomplete"
        INCOMPLETE_EXPIRED = "incomplete_expired", "Incomplete expired"
        UNPAID = "unpaid", "Unpaid"
        PAST_DUE = "past_due", "Past due"

    class Interval(models.TextChoices):
        MONTH = "month", "Month"
        YEAR = "year", "Year"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=32, choices=Status.choices)
    plan_interval = models.CharField(
        max_length=16,
        choices=Interval.choices,
        default=Interval.MONTH,
    )
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self) -> str:
        return f"Subscription for {self.user} ({self.status})"
