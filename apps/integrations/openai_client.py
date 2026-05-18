from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any, cast

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_TIMEOUT_SECONDS = 45.0

EXTENSION_TO_MIME: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _api_key() -> str:
    return str(getattr(settings, "OPENAI_API_KEY", "") or "")


def _model() -> str:
    return str(
        getattr(settings, "OPENAI_MODEL", "gpt-4.1-mini") or "gpt-4.1-mini"
    )


def is_configured() -> bool:
    return bool(_api_key())


def _encode_image(image_bytes: bytes, suffix: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    mime_type = EXTENSION_TO_MIME.get(suffix.lower(), "image/jpeg")
    return f"data:{mime_type};base64,{encoded}"


def _extract_json_payload(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]).strip()

    payload = json.loads(cleaned)
    if not isinstance(payload, dict):
        msg = "OpenAI response payload must be a JSON object."
        raise TypeError(msg)

    return cast(dict[str, Any], payload)


async def extract_receipt_fields_from_path(file_path: Path) -> dict[str, Any]:
    """Send a receipt image to OpenAI and return the raw extracted JSON dict.

    This is a dumb pipe. No Django models, no domain logic. The caller is
    responsible for validating and persisting the result.
    """

    if not is_configured():
        return {}

    image_bytes = file_path.read_bytes()
    return await extract_receipt_fields_from_bytes(
        image_bytes, file_path.suffix
    )


async def extract_receipt_fields_from_bytes(
    image_bytes: bytes, suffix: str
) -> dict[str, Any]:
    if not is_configured():
        return {}

    data_uri = _encode_image(image_bytes, suffix)

    system_prompt = (
        "Du är en svensk bokförings-assistent som läser kvitton. "
        "Du returnerar ENDAST giltig JSON, ingen markdown, inga kommentarer, ingen prosa. "
        "Alla textvärden ska vara på svenska."
    )

    user_instruction = (
        "Extrahera kvittouppgifter och returnera ett JSON-objekt med exakt dessa nycklar:\n"
        "  - vendor (string): leverantörens namn som det står på kvittot\n"
        "  - total_amount (number): totalbelopp inklusive moms i SEK\n"
        "  - vat_amount (number): momsbelopp i SEK\n"
        "  - date (string): kvittots datum i formatet YYYY-MM-DD\n"
        "  - category (string): kategori på SVENSKA, välj den mest passande från listan nedan\n"
        "  - note (string): kort anteckning på svenska om det är användbart, annars tom sträng\n"
        "\n"
        "KATEGORIER (svara med exakt en av dessa, på svenska):\n"
        "  - Diesel          (för dieselbränsle till maskiner, traktor, motorsåg etc.)\n"
        "  - Bensin          (för bensin till motorsåg, röjsåg, fyrhjuling etc.)\n"
        "  - Drivmedel       (om typen av bränsle inte framgår tydligt)\n"
        "  - Verktyg & material\n"
        "  - Reservdelar\n"
        "  - Frakt\n"
        "  - Försäkring\n"
        "  - Skogsvård       (gödsling, dikning, vägunderhåll)\n"
        "  - Avverkning      (entreprenörstjänster för avverkning)\n"
        "  - Plantering      (plantor, plantering, hjälpplantering)\n"
        "  - Maskinhyra\n"
        "  - Bokföring/revisor\n"
        "  - Resa            (kost, logi, parkering vid skogsbesök)\n"
        "  - Telefoni\n"
        "  - Annat           (endast om inget annat passar)\n"
        "\n"
        "DRIVMEDELSREGLER:\n"
        "  - Står det 'Diesel', 'EVO Diesel', 'HVO', 'B7' eller liknande → Diesel\n"
        "  - Står det 'Bensin', '95', '98', 'E5', 'E10', 'Alkylatbensin' eller liknande → Bensin\n"
        "  - Bensinstation utan tydlig bränsletyp → Drivmedel\n"
        "\n"
        "VIKTIGT:\n"
        "  - Använd PUNKT som decimaltecken (441.80, inte 441,80)\n"
        "  - Om ett fält inte kan utläsas, sätt det till null eller tom sträng\n"
        "  - Returnera ENDAST JSON-objektet, inget annat"
    )

    payload: dict[str, Any] = {
        "model": _model(),
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_instruction},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            },
        ],
    }

    headers = {"Authorization": f"Bearer {_api_key()}"}

    async with httpx.AsyncClient(timeout=OPENAI_TIMEOUT_SECONDS) as client:
        response = await client.post(
            OPENAI_API_URL, headers=headers, json=payload
        )

    response.raise_for_status()
    completion = response.json()

    try:
        content = completion["choices"][0]["message"]["content"]
        return _extract_json_payload(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        logger.warning("openai_client.parse_failed", exc_info=True)
        return {}
