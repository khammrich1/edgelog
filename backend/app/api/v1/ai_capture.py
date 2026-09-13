"""AI screenshot trade capture (VS3): extracts candidate trade fields from a
broker screenshot for the user to review and edit. Never creates or modifies
a Trade -- the client must still submit the normal create-trade request."""
import base64
import json
import logging

import anthropic
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.ai_capture import ScreenshotTradeExtraction

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "symbol": {"type": ["string", "null"]},
        "direction": {"anyOf": [{"type": "string", "enum": ["long", "short"]}, {"type": "null"}]},
        "entry_price": {"type": ["string", "null"]},
        "stop_price": {"type": ["string", "null"]},
        "target_price": {"type": ["string", "null"]},
        "initial_quantity": {"type": ["integer", "null"]},
        "notes": {"type": ["string", "null"]},
    },
    "required": [
        "symbol",
        "direction",
        "entry_price",
        "stop_price",
        "target_price",
        "initial_quantity",
        "notes",
    ],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You extract trade details from a screenshot of a broker or trading \
platform for a trading journal app. Only report a field if you can read it directly \
and confidently from the image. If a field is not visible, illegible, or ambiguous, \
return null for it rather than guessing or estimating.

Fields:
- symbol: the traded instrument's ticker/symbol, uppercase (e.g. "MNQ", "ES").
- direction: "long" if the position is long/buy, "short" if short/sell, else null.
- entry_price: the entry/fill price as a plain decimal string with no currency \
symbol, commas, or units (e.g. "24500.25"). Null if not visible.
- stop_price: the stop-loss price as a plain decimal string, or null if none is shown.
- target_price: the take-profit/target price as a plain decimal string, or null if \
none is shown.
- initial_quantity: the number of contracts/shares/units, as an integer, or null.
- notes: a single short sentence noting anything ambiguous or worth the user's \
attention (e.g. conflicting numbers, unclear direction). Null if nothing to flag.

Never fabricate a value. When in doubt, return null for that field."""


def _extract_trade_details_via_claude(image_bytes: bytes, content_type: str) -> dict:
    """Isolated so tests can monkeypatch this without calling the real API."""
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Screenshot trade capture is not configured on this server",
        )

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    image_b64 = base64.b64encode(image_bytes).decode("ascii")

    try:
        response = client.messages.create(
            model="claude-opus-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            output_config={
                "format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA},
                "effort": "low",
            },
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": content_type,
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Extract the trade details from this screenshot.",
                        },
                    ],
                }
            ],
        )
    except anthropic.RateLimitError:
        logger.warning("Screenshot capture rate-limited by Anthropic", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Screenshot capture is rate-limited right now. Try again shortly, or enter the trade manually.",
        )
    except anthropic.APIConnectionError:
        logger.error("Could not reach Anthropic for screenshot capture", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the screenshot capture service. Enter the trade manually.",
        )
    except anthropic.APIStatusError:
        logger.error("Anthropic returned an error status during screenshot capture", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Screenshot capture failed. Enter the trade manually.",
        )

    text_block = next(block.text for block in response.content if block.type == "text")
    return json.loads(text_block)


@router.post("/trades/parse-screenshot", response_model=ScreenshotTradeExtraction)
async def parse_trade_screenshot(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image is too large (max 5MB)")

    extracted = _extract_trade_details_via_claude(contents, file.content_type)
    return ScreenshotTradeExtraction(**extracted)
