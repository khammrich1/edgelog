"""AI screenshot capture for the Financial Tracker: extracts candidate
expense/income fields from a receipt/payout/eval-fee screenshot for the
user to review. Never creates a FinancialEntry -- the client must still
submit the normal create request. The bulk endpoint additionally reads
(never writes) the database, to flag rows that look like duplicates of an
entry the user already has."""
import base64
import json
import logging
from datetime import date as date_type
from decimal import Decimal, InvalidOperation

import anthropic
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.financial_entries import FinancialEntry
from app.models.user import User
from app.schemas.financial_entries import FinancialEntryBulkExtractionItem, FinancialEntryExtraction

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
- firm: the prop firm or broker's own name/brand (e.g. "TopStep", "Apex", \
"MyFundedFutures") -- look at page branding, logos, or titles, not just the \
row itself. This is NEVER an account number or account ID string (e.g. \
"EXPRESS-V2-CT-22568-98480289" is an account ID, not a firm name) -- if the \
only identifier visible is an account number, put it in notes instead and \
return null for firm. Null if no firm/brand name is identifiable anywhere \
in the image.
- notes: a single short sentence noting anything ambiguous or worth the \
user's attention. Null if nothing to flag.

Never fabricate a value. When in doubt, return null for that field."""

_BULK_ENTRY_ITEM_SCHEMA = {
    "type": "object",
    "properties": EXTRACTION_SCHEMA["properties"],
    "required": EXTRACTION_SCHEMA["required"],
    "additionalProperties": False,
}

BULK_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "entries": {"type": "array", "items": _BULK_ENTRY_ITEM_SCHEMA},
    },
    "required": ["entries"],
    "additionalProperties": False,
}

BULK_SYSTEM_PROMPT = """You extract financial ledger details from a screenshot for a \
prop-firm trading-business expense/income tracker. The screenshot may show a \
single receipt/payout, or a table/list of several separate payouts or \
expenses (e.g. a "payout history" page). Find every distinct row and return \
one entry per row, even if there is only one. Only report a field if you can \
read it directly and confidently from the image. If a field is not visible, \
illegible, or ambiguous for a given row, return null for it rather than \
guessing.

Per-row fields:
- entry_type: "expense" if this represents money paid out (evaluation fee, \
funded-account deposit, data/platform subscription, or any other cost), \
"income" if it represents money received (a payout, profit split, or \
reimbursement). Null if it can't be told from the image.
- category: a short free-text label for what this is, e.g. "evaluation fee", \
"payout", "funded account deposit", "data subscription". Null if unclear.
- amount: the dollar amount as a plain decimal string with no currency \
symbol, commas, or units (e.g. "149.00"). Null if not visible. If a row \
shows both a requested amount and a different finalized/paid amount, use \
the finalized/paid amount.
- date: the date this occurred, as "YYYY-MM-DD", or null if no date is visible.
- firm: the prop firm or broker's own name/brand (e.g. "TopStep", "Apex", \
"MyFundedFutures") -- look at page branding, logos, or titles, not just the \
row itself. This is NEVER an account number or account ID string (e.g. \
"EXPRESS-V2-CT-22568-98480289" is an account ID, not a firm name) -- if the \
only identifier visible for a row is an account number, put it in that \
row's notes instead and return null for firm. A single firm/brand shown \
once in the page header applies to every row from that page. Null if no \
firm/brand name is identifiable anywhere in the image.
- notes: a single short sentence noting anything ambiguous or worth the \
user's attention about that specific row. Null if nothing to flag.

Never fabricate a value. When in doubt, return null for that field. Return \
the "entries" array in the same order the rows appear in the image."""


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


def _extract_financial_entries_bulk_via_claude(image_bytes: bytes, content_type: str) -> list[dict]:
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
            max_tokens=4096,
            system=BULK_SYSTEM_PROMPT,
            output_config={
                "format": {"type": "json_schema", "schema": BULK_EXTRACTION_SCHEMA},
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
                        {
                            "type": "text",
                            "text": "Extract every financial entry row from this screenshot.",
                        },
                    ],
                }
            ],
        )
    except anthropic.RateLimitError:
        logger.warning("Bulk financial screenshot capture rate-limited by Anthropic", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Screenshot capture is rate-limited right now. Try again shortly, or enter it manually.",
        )
    except anthropic.APIConnectionError:
        logger.error("Could not reach Anthropic for bulk financial screenshot capture", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the screenshot capture service. Enter it manually.",
        )
    except anthropic.APIStatusError:
        logger.error("Anthropic returned an error status during bulk financial screenshot capture", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Screenshot capture failed. Enter it manually.",
        )

    text_block = next(block.text for block in response.content if block.type == "text")
    return json.loads(text_block)["entries"]


async def _flag_possible_duplicates(db: AsyncSession, user_id: int, extracted: list[dict]) -> list[dict]:
    """Marks a row as possible_duplicate when an existing entry for this
    user already matches its date, amount, and category. Rows with a
    missing/unparseable date, amount, or category are never flagged --
    there isn't enough to match on."""
    for entry in extracted:
        entry["possible_duplicate"] = False
        if not (entry.get("date") and entry.get("category") and entry.get("amount") is not None):
            continue
        try:
            parsed_date = date_type.fromisoformat(entry["date"])
            parsed_amount = Decimal(str(entry["amount"]))
        except (ValueError, InvalidOperation):
            continue

        result = await db.execute(
            select(FinancialEntry.id).where(
                FinancialEntry.user_id == user_id,
                FinancialEntry.date == parsed_date,
                FinancialEntry.amount == parsed_amount,
                FinancialEntry.category == entry["category"],
            )
        )
        if result.scalar_one_or_none() is not None:
            entry["possible_duplicate"] = True

    return extracted


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


@router.post("/financial-entries/parse-screenshot-bulk", response_model=list[FinancialEntryBulkExtractionItem])
async def parse_financial_entries_bulk_screenshot(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image is too large (max 5MB)")

    extracted = _extract_financial_entries_bulk_via_claude(contents, file.content_type)
    extracted = await _flag_possible_duplicates(db, current_user.id, extracted)
    return [FinancialEntryBulkExtractionItem(**entry) for entry in extracted]
