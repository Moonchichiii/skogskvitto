from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser


def user_display(user: AbstractBaseUser) -> str:
    email = getattr(user, "email", "")
    if email:
        return str(email)

    return f"Användare #{user.pk}"
