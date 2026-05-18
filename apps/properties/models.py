from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Property(models.Model):
    """A bookkeeping unit — typically a forest/farm property like 'Kråksjö säteri'.

    Each user has at least one Property (auto-created at signup as 'Min fastighet').
    Premium users can have multiple. All TaxYears, Receipts, Trips, etc. are
    scoped to a Property.

    `slug` is derived from `name` and stable within a user — used in URLs.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="properties",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    is_default = models.BooleanField(
        default=False,
        help_text="The fallback property when the user hasn't picked one. Exactly one per user.",
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "slug"],
                name="unique_owner_slug",
            ),
            models.UniqueConstraint(
                fields=["owner"],
                condition=models.Q(is_default=True),
                name="unique_default_property_per_user",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "name"]),
        ]
        ordering = ["-is_default", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base = slugify(self.name) or "fastighet"
            # Make slug unique within this user's properties
            slug = base
            counter = 2
            while (
                type(self).objects.filter(owner=self.owner, slug=slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
