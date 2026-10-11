"""Analytics and usage tracking endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, List

from app.db.database import get_db
from app.services.analytics_service import AnalyticsService
from app.security.auth import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/user/stats")
async def get_user_stats(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Get usage statistics for current user."""
    analytics = AnalyticsService(db)
    stats = analytics.get_user_stats(current_user['id'], days=days)
    return stats


@router.get("/aggregate/stats")
async def get_aggregate_stats(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Get aggregate statistics (admin only)."""
    if not current_user.get('is_admin', False):
        return {"error": "Admin access required"}

    analytics = AnalyticsService(db)
    stats = analytics.get_aggregate_stats(days=days)
    return stats


@router.get("/top-users")
async def get_top_users(
    metric: str = "events",
    limit: int = 10,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> List[Dict]:
    """Get top users by metric (admin only)."""
    if not current_user.get('is_admin', False):
        return []

    analytics = AnalyticsService(db)
    top_users = analytics.get_top_users(metric=metric, limit=limit, days=days)
    return top_users
