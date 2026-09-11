"""Daily Journal endpoints (VS2): trading days and the morning checklist."""
import uuid
from datetime import date as date_type
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.journal import ChecklistItem, TradingDay, TradingDayChecklistItem
from app.models.user import User
from app.schemas.journal import (
    ChecklistCompletionRead,
    ChecklistCompletionUpdate,
    ChecklistItemCreate,
    ChecklistItemRead,
    ChecklistItemUpdate,
    TradingDayRead,
    TradingDaySummary,
    TradingDayUpdate,
)

router = APIRouter()

BIAS_CHART_DIR = Path(__file__).resolve().parents[3] / "uploads" / "bias_charts"
ALLOWED_IMAGE_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

LOCKED_DAY_DETAIL = "Day is locked. Unlock it to make changes."


# ---- Checklist item configuration ----

@router.get("/checklist-items", response_model=list[ChecklistItemRead])
async def list_checklist_items(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(ChecklistItem).where(ChecklistItem.user_id == current_user.id)
    if not include_inactive:
        query = query.where(ChecklistItem.is_active.is_(True))
    query = query.order_by(ChecklistItem.sort_order, ChecklistItem.id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/checklist-items", response_model=ChecklistItemRead, status_code=status.HTTP_201_CREATED)
async def create_checklist_item(
    payload: ChecklistItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    max_order_result = await db.execute(
        select(func.max(ChecklistItem.sort_order)).where(ChecklistItem.user_id == current_user.id)
    )
    next_order = (max_order_result.scalar() or 0) + 1

    item = ChecklistItem(user_id=current_user.id, label=payload.label, sort_order=next_order)
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@router.put("/checklist-items/{item_id}", response_model=ChecklistItemRead)
async def update_checklist_item(
    item_id: int,
    payload: ChecklistItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await _get_owned_checklist_item(db, current_user.id, item_id)

    if payload.label is not None:
        item.label = payload.label
    if payload.sort_order is not None:
        item.sort_order = payload.sort_order
    if payload.is_active is not None:
        item.is_active = payload.is_active

    await db.flush()
    await db.refresh(item)
    return item


@router.delete("/checklist-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_checklist_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await _get_owned_checklist_item(db, current_user.id, item_id)
    # Soft delete: a past day's record of completing this item must survive
    # the item being removed from the active checklist.
    item.is_active = False
    await db.flush()


async def _get_owned_checklist_item(db: AsyncSession, user_id: int, item_id: int) -> ChecklistItem:
    result = await db.execute(
        select(ChecklistItem).where(ChecklistItem.id == item_id, ChecklistItem.user_id == user_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist item not found")
    return item


# ---- Trading days ----

@router.get("/days", response_model=list[TradingDaySummary])
async def list_trading_days(
    start: date_type,
    end: date_type,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if end < start:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end must not be before start")

    result = await db.execute(
        select(TradingDay).where(
            TradingDay.user_id == current_user.id,
            TradingDay.date >= start,
            TradingDay.date <= end,
        )
    )
    days = result.scalars().all()

    summaries = []
    for day in days:
        completion_result = await db.execute(
            select(TradingDayChecklistItem).where(TradingDayChecklistItem.trading_day_id == day.id)
        )
        completions = completion_result.scalars().all()
        summaries.append(
            TradingDaySummary(
                date=day.date,
                status=day.status,
                has_bias_chart=day.bias_chart_path is not None,
                checklist_completed_count=sum(1 for c in completions if c.completed),
                checklist_total_count=len(completions),
            )
        )
    return summaries


@router.get("/days/{day}", response_model=TradingDayRead)
async def get_trading_day(
    day: date_type,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_or_create_trading_day(db, current_user.id, day)
    return await _serialize_trading_day(db, trading_day)


@router.put("/days/{day}", response_model=TradingDayRead)
async def update_trading_day(
    day: date_type,
    payload: TradingDayUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_or_create_trading_day(db, current_user.id, day)
    _require_unlocked(trading_day)

    if payload.sleep_quality is not None:
        trading_day.sleep_quality = payload.sleep_quality
    if payload.mood is not None:
        trading_day.mood = payload.mood
    if payload.market_bias is not None:
        trading_day.market_bias = payload.market_bias

    await db.flush()
    await db.refresh(trading_day)
    return await _serialize_trading_day(db, trading_day)


@router.put("/days/{day}/checklist/{item_id}", response_model=TradingDayRead)
async def update_checklist_completion(
    day: date_type,
    item_id: int,
    payload: ChecklistCompletionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_or_create_trading_day(db, current_user.id, day)
    _require_unlocked(trading_day)

    result = await db.execute(
        select(TradingDayChecklistItem).where(
            TradingDayChecklistItem.trading_day_id == trading_day.id,
            TradingDayChecklistItem.checklist_item_id == item_id,
        )
    )
    completion = result.scalar_one_or_none()
    if completion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist item not found for this day")

    completion.completed = payload.completed
    await db.flush()
    await db.refresh(trading_day)
    return await _serialize_trading_day(db, trading_day)


@router.post("/days/{day}/lock", response_model=TradingDayRead)
async def lock_trading_day(
    day: date_type,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_or_create_trading_day(db, current_user.id, day)
    trading_day.status = "locked"
    await db.flush()
    await db.refresh(trading_day)
    return await _serialize_trading_day(db, trading_day)


@router.post("/days/{day}/unlock", response_model=TradingDayRead)
async def unlock_trading_day(
    day: date_type,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_or_create_trading_day(db, current_user.id, day)
    trading_day.status = "draft"
    await db.flush()
    await db.refresh(trading_day)
    return await _serialize_trading_day(db, trading_day)


@router.post("/days/{day}/bias-chart", response_model=TradingDayRead)
async def upload_bias_chart(
    day: date_type,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_or_create_trading_day(db, current_user.id, day)
    _require_unlocked(trading_day)

    extension = ALLOWED_IMAGE_TYPES.get(file.content_type)
    if extension is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image is too large (max 5MB)")

    BIAS_CHART_DIR.mkdir(parents=True, exist_ok=True)
    _remove_existing_bias_chart(trading_day)

    filename = f"{uuid.uuid4().hex}.{extension}"
    (BIAS_CHART_DIR / filename).write_bytes(contents)

    trading_day.bias_chart_path = filename
    await db.flush()
    await db.refresh(trading_day)
    return await _serialize_trading_day(db, trading_day)


@router.get("/days/{day}/bias-chart")
async def get_bias_chart(
    day: date_type,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TradingDay).where(TradingDay.user_id == current_user.id, TradingDay.date == day)
    )
    trading_day = result.scalar_one_or_none()
    if trading_day is None or trading_day.bias_chart_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No bias chart for this day")

    file_path = BIAS_CHART_DIR / trading_day.bias_chart_path
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bias chart file missing")

    return FileResponse(file_path)


@router.delete("/days/{day}/bias-chart", response_model=TradingDayRead)
async def delete_bias_chart(
    day: date_type,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    trading_day = await _get_or_create_trading_day(db, current_user.id, day)
    _require_unlocked(trading_day)

    _remove_existing_bias_chart(trading_day)
    trading_day.bias_chart_path = None
    await db.flush()
    await db.refresh(trading_day)
    return await _serialize_trading_day(db, trading_day)


def _require_unlocked(trading_day: TradingDay) -> None:
    if trading_day.status == "locked":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=LOCKED_DAY_DETAIL)


def _remove_existing_bias_chart(trading_day: TradingDay) -> None:
    if trading_day.bias_chart_path:
        existing_path = BIAS_CHART_DIR / trading_day.bias_chart_path
        if existing_path.exists():
            existing_path.unlink()


async def _get_or_create_trading_day(db: AsyncSession, user_id: int, day: date_type) -> TradingDay:
    result = await db.execute(
        select(TradingDay).where(TradingDay.user_id == user_id, TradingDay.date == day)
    )
    trading_day = result.scalar_one_or_none()
    if trading_day is None:
        trading_day = TradingDay(user_id=user_id, date=day, status="draft")
        db.add(trading_day)
        await db.flush()
        await db.refresh(trading_day)

    # Ensure a completion row exists for every currently-active checklist
    # item, so the checklist config can change over time without needing a
    # separate "start my day" step.
    active_items_result = await db.execute(
        select(ChecklistItem).where(ChecklistItem.user_id == user_id, ChecklistItem.is_active.is_(True))
    )
    active_items = active_items_result.scalars().all()

    existing_result = await db.execute(
        select(TradingDayChecklistItem.checklist_item_id).where(
            TradingDayChecklistItem.trading_day_id == trading_day.id
        )
    )
    existing_item_ids = set(existing_result.scalars().all())

    added = False
    for item in active_items:
        if item.id not in existing_item_ids:
            db.add(
                TradingDayChecklistItem(trading_day_id=trading_day.id, checklist_item_id=item.id, completed=False)
            )
            added = True

    if added:
        await db.flush()

    return trading_day


async def _serialize_trading_day(db: AsyncSession, trading_day: TradingDay) -> TradingDayRead:
    result = await db.execute(
        select(TradingDayChecklistItem, ChecklistItem)
        .join(ChecklistItem, TradingDayChecklistItem.checklist_item_id == ChecklistItem.id)
        .where(TradingDayChecklistItem.trading_day_id == trading_day.id)
        .order_by(ChecklistItem.sort_order, ChecklistItem.id)
    )
    rows = result.all()
    checklist = [
        ChecklistCompletionRead(checklist_item_id=item.id, label=item.label, completed=completion.completed)
        for completion, item in rows
    ]
    return TradingDayRead(
        id=trading_day.id,
        date=trading_day.date,
        status=trading_day.status,
        sleep_quality=trading_day.sleep_quality,
        mood=trading_day.mood,
        market_bias=trading_day.market_bias,
        has_bias_chart=trading_day.bias_chart_path is not None,
        checklist=checklist,
        created_at=trading_day.created_at,
        updated_at=trading_day.updated_at,
    )
