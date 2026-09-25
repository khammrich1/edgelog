"""Site-traffic beacon: the frontend pings this on every route change so
the admin page can show a traffic table. Works identically for logged-in
and anonymous visitors, and must never fail the caller's navigation."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.api.deps import get_current_user_optional
from app.core.database import get_db
from app.models.page_view import PageView
from app.models.user import User
from app.schemas.admin import PageViewCreate

router = APIRouter()


@router.post("/track/pageview", status_code=status.HTTP_204_NO_CONTENT)
async def track_pageview(
    payload: PageViewCreate,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    db.add(PageView(user_id=current_user.id if current_user else None, path=payload.path))
    await db.flush()
