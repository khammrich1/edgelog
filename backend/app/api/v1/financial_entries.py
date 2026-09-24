"""Annual P&L / Financial Tracker endpoints: a flat cash ledger, independent
of Trade/TradingDay."""
import uuid
from datetime import date as date_type
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.financial_entries import FinancialEntry
from app.models.user import User
from app.schemas.financial_entries import (
    FinancialEntryBulkCreate,
    FinancialEntryCreate,
    FinancialEntryRead,
    FinancialEntryUpdate,
)

router = APIRouter()

FINANCIAL_SCREENSHOT_DIR = Path(__file__).resolve().parents[3] / "uploads" / "financial_screenshots"
ALLOWED_IMAGE_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


async def _get_owned_entry(db: AsyncSession, user_id: int, entry_id: int) -> FinancialEntry:
    result = await db.execute(
        select(FinancialEntry).where(FinancialEntry.id == entry_id, FinancialEntry.user_id == user_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Financial entry not found")
    return entry


def _serialize_entry(entry: FinancialEntry) -> FinancialEntryRead:
    return FinancialEntryRead(
        id=entry.id,
        entry_type=entry.entry_type,
        category=entry.category,
        amount=entry.amount,
        date=entry.date,
        firm=entry.firm,
        notes=entry.notes,
        has_screenshot=entry.screenshot_path is not None,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


# ---- CRUD ----

@router.get("/financial-entries", response_model=list[FinancialEntryRead])
async def list_financial_entries(
    start: date_type,
    end: date_type,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if end < start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end must not be before start")

    result = await db.execute(
        select(FinancialEntry)
        .where(
            FinancialEntry.user_id == current_user.id,
            FinancialEntry.date >= start,
            FinancialEntry.date <= end,
        )
        .order_by(FinancialEntry.date, FinancialEntry.id)
    )
    return [_serialize_entry(e) for e in result.scalars().all()]


@router.post("/financial-entries", response_model=FinancialEntryRead, status_code=status.HTTP_201_CREATED)
async def create_financial_entry(
    payload: FinancialEntryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = FinancialEntry(
        user_id=current_user.id,
        entry_type=payload.entry_type,
        category=payload.category,
        amount=payload.amount,
        date=payload.date,
        firm=payload.firm,
        notes=payload.notes,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return _serialize_entry(entry)


@router.post("/financial-entries/bulk", response_model=list[FinancialEntryRead], status_code=status.HTTP_201_CREATED)
async def bulk_create_financial_entries(
    payload: FinancialEntryBulkCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entries = [
        FinancialEntry(
            user_id=current_user.id,
            entry_type=item.entry_type,
            category=item.category,
            amount=item.amount,
            date=item.date,
            firm=item.firm,
            notes=item.notes,
        )
        for item in payload.entries
    ]
    db.add_all(entries)
    await db.flush()
    for entry in entries:
        await db.refresh(entry)
    return [_serialize_entry(entry) for entry in entries]


@router.get("/financial-entries/{entry_id}", response_model=FinancialEntryRead)
async def get_financial_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await _get_owned_entry(db, current_user.id, entry_id)
    return _serialize_entry(entry)


@router.put("/financial-entries/{entry_id}", response_model=FinancialEntryRead)
async def update_financial_entry(
    entry_id: int,
    payload: FinancialEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await _get_owned_entry(db, current_user.id, entry_id)

    if payload.entry_type is not None:
        entry.entry_type = payload.entry_type
    if payload.category is not None:
        entry.category = payload.category
    if payload.amount is not None:
        entry.amount = payload.amount
    if payload.date is not None:
        entry.date = payload.date
    if payload.firm is not None:
        entry.firm = payload.firm
    if payload.notes is not None:
        entry.notes = payload.notes

    await db.flush()
    await db.refresh(entry)
    return _serialize_entry(entry)


@router.delete("/financial-entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_financial_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await _get_owned_entry(db, current_user.id, entry_id)
    await db.delete(entry)
    await db.flush()


# ---- Screenshot storage ----

def _remove_existing_entry_screenshot(entry: FinancialEntry) -> None:
    if entry.screenshot_path:
        existing = FINANCIAL_SCREENSHOT_DIR / entry.screenshot_path
        if existing.exists():
            existing.unlink()
        entry.screenshot_path = None


@router.post("/financial-entries/{entry_id}/screenshot", response_model=FinancialEntryRead)
async def upload_financial_entry_screenshot(
    entry_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await _get_owned_entry(db, current_user.id, entry_id)

    extension = ALLOWED_IMAGE_TYPES.get(file.content_type)
    if extension is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image is too large (max 5MB)")

    FINANCIAL_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    _remove_existing_entry_screenshot(entry)

    filename = f"{uuid.uuid4().hex}.{extension}"
    (FINANCIAL_SCREENSHOT_DIR / filename).write_bytes(contents)

    entry.screenshot_path = filename
    await db.flush()
    await db.refresh(entry)
    return _serialize_entry(entry)


@router.get("/financial-entries/{entry_id}/screenshot")
async def get_financial_entry_screenshot(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await _get_owned_entry(db, current_user.id, entry_id)
    if entry.screenshot_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No screenshot for this entry")

    file_path = FINANCIAL_SCREENSHOT_DIR / entry.screenshot_path
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screenshot file missing")

    return FileResponse(file_path)


@router.delete("/financial-entries/{entry_id}/screenshot", response_model=FinancialEntryRead)
async def delete_financial_entry_screenshot(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    entry = await _get_owned_entry(db, current_user.id, entry_id)
    _remove_existing_entry_screenshot(entry)
    await db.flush()
    await db.refresh(entry)
    return _serialize_entry(entry)
