"""Admin-only views: account roster, site traffic, and submitted feedback.
Every route here is gated by get_current_admin_user."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user
from app.core.database import get_db
from app.models.feedback import Feedback
from app.models.page_view import PageView
from app.models.user import User
from app.schemas.admin import AccountRosterEntry, FeedbackEntry, TrafficRow

router = APIRouter()

TRAFFIC_WINDOW = timedelta(days=7)


@router.get("/admin/roster", response_model=list[AccountRosterEntry])
async def get_account_roster(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    latest_views = (
        select(
            PageView.user_id,
            PageView.path,
            PageView.created_at,
            func.row_number()
            .over(partition_by=PageView.user_id, order_by=PageView.created_at.desc())
            .label("rn"),
        )
        .where(PageView.user_id.is_not(None))
        .subquery()
    )

    result = await db.execute(
        select(User, latest_views.c.path, latest_views.c.created_at)
        .outerjoin(
            latest_views,
            (latest_views.c.user_id == User.id) & (latest_views.c.rn == 1),
        )
        .order_by(User.created_at)
    )

    return [
        AccountRosterEntry(
            id=user.id,
            email=user.email,
            is_admin=user.is_admin,
            created_at=user.created_at,
            last_activity_at=last_seen,
            last_activity_path=last_path,
        )
        for user, last_path, last_seen in result.all()
    ]


@router.get("/admin/traffic", response_model=list[TrafficRow])
async def get_traffic(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - TRAFFIC_WINDOW

    auth_case = case((PageView.user_id.is_not(None), 1), else_=0)
    unauth_case = case((PageView.user_id.is_(None), 1), else_=0)

    result = await db.execute(
        select(
            PageView.path,
            func.count().label("hits"),
            func.count(func.distinct(PageView.user_id)).label("unique_auth_users"),
            func.sum(auth_case).label("auth_hits"),
            func.sum(unauth_case).label("unauth_hits"),
        )
        .where(PageView.created_at >= since)
        .group_by(PageView.path)
        .order_by(func.count().desc())
    )

    return [
        TrafficRow(
            path=row.path,
            hits=row.hits,
            unique_auth_users=row.unique_auth_users,
            auth_hits=row.auth_hits or 0,
            unauth_hits=row.unauth_hits or 0,
        )
        for row in result.all()
    ]


@router.get("/admin/feedback", response_model=list[FeedbackEntry])
async def get_feedback(
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Feedback, User.email)
        .outerjoin(User, User.id == Feedback.user_id)
        .order_by(Feedback.created_at.desc(), Feedback.id.desc())
    )

    return [
        FeedbackEntry(id=feedback.id, user_email=email, message=feedback.message, created_at=feedback.created_at)
        for feedback, email in result.all()
    ]
