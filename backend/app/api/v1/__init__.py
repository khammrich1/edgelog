"""API v1 router."""
from fastapi import APIRouter
from .ai_capture import router as ai_capture_router
from .auth import router as auth_router
from .journal import router as journal_router
from .trades import router as trades_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(journal_router, prefix="/journal", tags=["journal"])
api_router.include_router(trades_router, prefix="/journal", tags=["trades"])
api_router.include_router(ai_capture_router, tags=["ai-capture"])
