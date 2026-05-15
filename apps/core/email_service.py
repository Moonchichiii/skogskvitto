from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_transactional_email(
    to: str,
    template: str,
    context: dict[str, Any],
) -> bool:
    """Render and send a transactional text email.

    Email failures are logged and returned as False so they do not block
    the user flow that triggered the email.
    """
    try:
        subject = str(context.get("subject", ""))
        body = render_to_string(template, context)

        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Transaktionsmail misslyckades (mall=%s)", template)
        return False
