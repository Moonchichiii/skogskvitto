"""Property domain selectors — read-side queries."""

from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser
from django.db.models import QuerySet

from apps.properties.models import Property


def user_properties(user: AbstractBaseUser) -> QuerySet[Property]:
    """All properties owned by this user, default first."""
    return Property.objects.filter(owner=user)


def default_property_for(user: AbstractBaseUser) -> Property | None:
    """Return the user's default property, or None if none exists."""
    return Property.objects.filter(owner=user, is_default=True).first()


def get_user_property_by_slug(user: AbstractBaseUser, slug: str) -> Property | None:
    """Look up a property by slug, scoped to this user."""
    return Property.objects.filter(owner=user, slug=slug).first()
