"""AI screenshot capture for the Financial Tracker: extracts candidate
expense/income fields from a receipt/payout/eval-fee screenshot for the
user to review. Never creates a FinancialEntry -- the client must still
submit the normal create request."""
import base64
import json
import logging

import anthropic
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.financial_entries import FinancialEntryExtraction

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "entry_type": {"anyOf": [{"type": "string", "enum": ["expense", "income"]}, {"type": "null"}]},
        "category": {"type": ["string", "null"]},
        "amount": {"type": ["string", "null"]},
        "date": {"type": ["string", "null"]},
        "firm": {"type": ["string", "null"]},
        "notes": {"type": ["string", "null"]},
    },
    "required": ["entry_type", "category", "amount", "date", "firm", "notes"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You extract financial ledger details from a screenshot for a \
prop-firm trading-business expense/income tracker. Only report a field if you \
can read it directly and confidently from the image. If a field is not \
visible, illegible, or ambiguous, return null for it rather than guessing.

Fields:
- entry_type: "expense" if this represents money paid out (evaluation fee, \
funded-account deposit, data/platform subscription, or any other cost), \
"income" if it represents money received (a payout, profit split, or \
reimbursement). Null if it can't be told from the image.
- category: a short free-text label for what this is, e.g. "evaluation fee", \
"payout", "funded account deposit", "data subscription". Null if unclear.
- amount: the dollar amount as a plain decimal string with no currency \
symbol, commas, or units (e.g. "149.00"). Null if not visible.
- date: the date this occurred, as "YYYY-MM-DD", or null if no date is visible.
- firm: the prop firm, broker, or account name shown, or null if none is \
visible.
- notes: a single short sentence noting anything ambiguous or worth the \
user's attention. Null if nothing to flag.

Never fabricate a value. When in doubt, return null for that field."""


def _extract_financial_entry_via_claude(image_bytes: bytes, content_type: str) -> dict:
    """Isolated so tests can monkeypatch this without calling the real API."""
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Screenshot capture is not configured on this server",
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
                            "source": {"type": "base64", "media_type": content_type, "data": image_b64},
                        },
                        {"type": "text", "text": "Extract the financial entry details from this screenshot."},
                    ],
                }
            ],
        )
    except anthropic.RateLimitError:
        logger.warning("Financial screenshot capture rate-limited by Anthropic", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Screenshot capture is rate-limited right now. Try again shortly, or enter it manually.",
        )
    except anthropic.APIConnectionError:
        logger.error("Could not reach Anthropic for financial screenshot capture", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the screenshot capture service. Enter it manually.",
        )
    except anthropic.APIStatusError:
        logger.error("Anthropic returned an error status during financial screenshot capture", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Screenshot capture failed. Enter it manually.",
        )

    text_block = next(block.text for block in response.content if block.type == "text")
    return json.loads(text_block)


@router.post("/financial-entries/parse-screenshot", response_model=FinancialEntryExtraction)
async def parse_financial_entry_screenshot(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image is too large (max 5MB)")

    extracted = _extract_financial_entry_via_claude(contents, file.content_type)
    return FinancialEntryExtraction(**extracted)
