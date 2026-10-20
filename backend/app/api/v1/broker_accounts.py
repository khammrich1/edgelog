"""Broker-account ownership registry (issue #95).

Lets a trader record which broker accounts they use, as their own
self-reported claim -- not a verified fact. No endpoint here, or
anywhere else in the codebase, can ever mark a claim "verified": there is
no provider-backed channel between EdgeLog's backend and TopstepX today
(the local Trader Agent never talks to this backend). Building that
channel, and the real verification it would enable, is explicitly
out of scope for this slice -- see issue #95.

This is pure registry CRUD: no trade data is read or written here, no
broker API is called, and nothing here changes how the existing
reconciliation-preview endpoint behaves (it still accepts any client-
supplied account_id, scoped by user_id, exactly as before).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.broker_accounts import BrokerAccount
from app.models.user import User
from app.schemas.broker_accounts import BrokerAccountCreate, BrokerAccountRead

DUPLICATE_CLAIM_DETAIL = "You've already registered this provider/account_id combination."

router = APIRouter()


@router.get("/broker-accounts", response_model=list[BrokerAccountRead])
async def list_broker_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BrokerAccount)
        .where(BrokerAccount.user_id == current_user.id)
        .order_by(BrokerAccount.created_at, BrokerAccount.id)
    )
    return result.scalars().all()


@router.post("/broker-accounts", response_model=BrokerAccountRead, status_code=status.HTTP_201_CREATED)
async def create_broker_account(
    payload: BrokerAccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registers a self-reported claim -- always created as
    "unverified". Registering the same (provider, account_id) you've
    already registered is rejected as a duplicate (409); registering one
    someone ELSE has already registered is allowed, since with no
    verification mechanism there is nothing to arbitrate that collision
    with one way or the other -- both rows simply stay unverified.

    The SELECT-then-INSERT below is a pre-check, not the real guarantee:
    two concurrent requests can both pass it before either commits. The
    `uq_broker_account_user_provider_account` index is what actually
    prevents the duplicate; a race that reaches the INSERT anyway is
    caught here and turned into the same 409, instead of surfacing as an
    unhandled 500 (owner review, PR #98)."""
    existing = await _find_existing_claim(db, current_user.id, payload.provider, payload.account_id)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_CLAIM_DETAIL)

    account = BrokerAccount(
        user_id=current_user.id,
        provider=payload.provider,
        account_id=payload.account_id,
        label=payload.label,
        verification_status="unverified",
    )
    db.add(account)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_CLAIM_DETAIL)

    await db.refresh(account)
    return account


async def _find_existing_claim(db: AsyncSession, user_id: int, provider: str, account_id: str):
    result = await db.execute(
        select(BrokerAccount).where(
            BrokerAccount.user_id == user_id,
            BrokerAccount.provider == provider,
            BrokerAccount.account_id == account_id,
        )
    )
    return result.scalar_one_or_none()


@router.delete("/broker-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_broker_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = await _get_owned_broker_account(db, current_user.id, account_id)
    await db.delete(account)
    await db.flush()


async def _get_owned_broker_account(db: AsyncSession, user_id: int, account_id: int) -> BrokerAccount:
    result = await db.execute(
        select(BrokerAccount).where(BrokerAccount.id == account_id, BrokerAccount.user_id == user_id)
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Broker account not found")
    return account


async def get_registered_account_ids_for_user(db: AsyncSession, user_id: int, provider: str) -> set[str]:
    """Reusable resolver for future account-scoped operations (issue #95
    deliverable #4): every account_id this user has REGISTERED for this
    provider, regardless of verification_status. Today that means
    "self-reported claims", not "verified ownership" -- there is nothing
    stronger to return yet. A future slice with real provider-backed
    verification should add a separate, verification_status="verified"-
    filtered resolver rather than strengthening this one's meaning out
    from under existing callers."""
    result = await db.execute(
        select(BrokerAccount.account_id).where(BrokerAccount.user_id == user_id, BrokerAccount.provider == provider)
    )
    return set(result.scalars().all())
