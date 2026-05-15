from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.template import Context, Template
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _render_transactional_template(
    template: str,
    context: dict[str, Any],
) -> str:
    try:
        return render_to_string(template, context)
    except TemplateDoesNotExist:
        fallback_path = Path(settings.BASE_DIR) / "templates" / template
        if not fallback_path.is_file():
            raise

        template_source = fallback_path.read_text(encoding="utf-8-sig")
        return Template(template_source).render(Context(context))


def send_transactional_email(
    to: str,
    template: str,
    context: dict[str, Any],
) -> bool:
    """Render and send a transactional text email.

    Email sending must not block non-email user flows, so failures are logged
    and returned as False.
    """
    try:
        subject = str(context.get("subject", ""))
        body = _render_transactional_template(template, context)

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
