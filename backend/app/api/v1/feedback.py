"""User-submitted feedback (one-way: message only, no reply workflow).
Viewing submitted feedback is an admin-only concern -- see api/v1/admin.py."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.admin import FeedbackCreate

router = APIRouter()


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    db.add(Feedback(user_id=current_user.id, message=payload.message))
    await db.flush()
