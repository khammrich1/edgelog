"""Admin traffic tracking: an append-only log of frontend route visits,
recorded via a client-side beacon on every navigation. This is analytics
data, not user-owned content -- rows survive independently of whether a
user is currently logged in (user_id is nullable for anonymous visits)."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class PageView(Base):
    __tablename__ = "page_views"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    path = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
