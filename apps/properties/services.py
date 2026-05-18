"""Property domain services — write-side operations."""

from __future__ import annotations

import logging

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction

from apps.properties.models import Property

logger = logging.getLogger(__name__)

DEFAULT_PROPERTY_NAME = "Min fastighet"


@transaction.atomic
def get_or_create_default_property(user: AbstractBaseUser) -> Property:
    """Return the user's default Property, creating one if missing.

    This is the safety net — Property is auto-created via signal at signup, but
    legacy users (created before this feature) need a backfill path.
    """
    existing = Property.objects.filter(owner=user, is_default=True).first()
    if existing is not None:
        return existing

    prop = Property.objects.create(
        owner=user,
        name=DEFAULT_PROPERTY_NAME,
        is_default=True,
    )
    logger.info(
        "properties.default_created",
        extra={"user_id": user.pk, "property_id": prop.pk},
    )
    return prop


@transaction.atomic
def rename_property(*, property_obj: Property, new_name: str) -> Property:
    """Rename a property. Slug is regenerated to match."""
    new_name = (new_name or "").strip()
    if not new_name:
        raise ValueError("Namn kan inte vara tomt.")
    if len(new_name) > 120:
        raise ValueError("Namn får vara max 120 tecken.")

    property_obj.name = new_name
    property_obj.slug = ""  # Force regen in save()
    property_obj.save()
    logger.info(
        "properties.renamed",
        extra={"property_id": property_obj.pk, "new_name": new_name},
    )
    return property_obj


@transaction.atomic
def create_additional_property(*, user: AbstractBaseUser, name: str) -> Property:
    """Create a non-default property for premium users.

    Caller is responsible for checking premium status.
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("Namn kan inte vara tomt.")
    if len(name) > 120:
        raise ValueError("Namn får vara max 120 tecken.")

    prop = Property.objects.create(
        owner=user,
        name=name,
        is_default=False,
    )
    logger.info(
        "properties.created_additional",
        extra={"user_id": user.pk, "property_id": prop.pk},
    )
    return prop
