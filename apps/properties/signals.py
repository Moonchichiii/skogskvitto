"""Signal handlers for Property auto-creation."""

from __future__ import annotations

import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender=settings.AUTH_USER_MODEL, dispatch_uid="create_default_property")
def create_default_property_on_user_signup(sender, instance, created, **kwargs) -> None:
    """Auto-create the user's default Property on first save."""
    if not created:
        return

    from apps.properties.services import get_or_create_default_property

    prop = get_or_create_default_property(instance)
    logger.info(
        "properties.signal.default_created_on_signup",
        extra={"user_id": instance.pk, "property_id": prop.pk},
    )
