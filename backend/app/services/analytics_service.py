"""Analytics and usage tracking service."""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import UsageEvent

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Track and analyze user activity."""

    def __init__(self, db: Session):
        """Initialize analytics service."""
        self.db = db

    def track_event(
        self,
        user_id: str,
        event_type: str,
        resource_type: Optional[str] = None,
        token_count: Optional[int] = None,
        latency_ms: Optional[float] = None,
        success: bool = True
    ) -> Dict:
        """
        Track a usage event.

        Args:
            user_id: User ID
            event_type: Event type (ask, upload, export, etc)
            resource_type: Type of resource (document, conversation)
            token_count: Number of tokens used (for LLM)
            latency_ms: Request latency in milliseconds
            success: Whether event succeeded

        Returns:
            Event dict
        """
        event = UsageEvent(
            id=str(uuid4()),
            user_id=user_id,
            event_type=event_type,
            resource_type=resource_type,
            token_count=token_count or 0,
            latency_ms=latency_ms,
            success=success
        )

        try:
            self.db.add(event)
            self.db.commit()
            logger.debug(f"Tracked event {event_type} for user {user_id}")
            return self._to_dict(event)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to track event: {e}")
            raise

    def get_user_stats(self, user_id: str, days: int = 30) -> Dict:
        """
        Get user statistics for a period.

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            Stats dict with aggregations
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        events = self.db.query(UsageEvent).filter(
            (UsageEvent.user_id == user_id) &
            (UsageEvent.created_at >= since)
        ).all()

        if not events:
            return {
                'user_id': user_id,
                'days': days,
                'total_events': 0,
                'events_by_type': {},
                'total_tokens': 0,
                'avg_latency_ms': 0,
                'success_rate': 0
            }

        # Calculate stats
        events_by_type = {}
        total_tokens = 0
        total_latency = 0
        latency_count = 0
        success_count = 0

        for event in events:
            if event.event_type not in events_by_type:
                events_by_type[event.event_type] = 0
            events_by_type[event.event_type] += 1

            total_tokens += event.token_count or 0

            if event.latency_ms is not None:
                total_latency += event.latency_ms
                latency_count += 1

            if event.success:
                success_count += 1

        avg_latency = total_latency / latency_count if latency_count > 0 else 0
        success_rate = success_count / len(events) if events else 0

        return {
            'user_id': user_id,
            'days': days,
            'total_events': len(events),
            'events_by_type': events_by_type,
            'total_tokens': total_tokens,
            'avg_latency_ms': round(avg_latency, 2),
            'success_rate': round(success_rate, 3)
        }

    def get_aggregate_stats(self, days: int = 30) -> Dict:
        """
        Get aggregate statistics across all users.

        Args:
            days: Number of days to look back

        Returns:
            Aggregate stats dict
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Total events
        total_events = self.db.query(func.count(UsageEvent.id)).filter(
            UsageEvent.created_at >= since
        ).scalar()

        # Events by type
        events_by_type = {}
        type_results = self.db.query(
            UsageEvent.event_type,
            func.count(UsageEvent.id)
        ).filter(
            UsageEvent.created_at >= since
        ).group_by(UsageEvent.event_type).all()

        for event_type, count in type_results:
            events_by_type[event_type] = count

        # Total tokens
        total_tokens = self.db.query(func.sum(UsageEvent.token_count)).filter(
            UsageEvent.created_at >= since
        ).scalar() or 0

        # Average latency
        avg_latency = self.db.query(func.avg(UsageEvent.latency_ms)).filter(
            UsageEvent.created_at >= since
        ).scalar() or 0

        # Success rate
        total_count = self.db.query(func.count(UsageEvent.id)).filter(
            UsageEvent.created_at >= since
        ).scalar()
        success_count = self.db.query(func.count(UsageEvent.id)).filter(
            (UsageEvent.created_at >= since) &
            (UsageEvent.success == True)
        ).scalar()
        success_rate = success_count / total_count if total_count > 0 else 0

        # Unique users
        unique_users = self.db.query(func.count(func.distinct(UsageEvent.user_id))).filter(
            UsageEvent.created_at >= since
        ).scalar()

        return {
            'period_days': days,
            'total_events': total_events,
            'unique_users': unique_users,
            'events_by_type': events_by_type,
            'total_tokens': int(total_tokens),
            'avg_latency_ms': round(float(avg_latency), 2),
            'success_rate': round(success_rate, 3)
        }

    def get_top_users(self, metric: str = 'events', limit: int = 10, days: int = 30) -> List[Dict]:
        """
        Get top users by metric.

        Args:
            metric: Metric to sort by (events, tokens, latency)
            limit: Number of users to return
            days: Number of days to look back

        Returns:
            List of user stats
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        query = self.db.query(
            UsageEvent.user_id,
            func.count(UsageEvent.id).label('event_count'),
            func.sum(UsageEvent.token_count).label('total_tokens'),
            func.avg(UsageEvent.latency_ms).label('avg_latency')
        ).filter(
            UsageEvent.created_at >= since
        ).group_by(UsageEvent.user_id)

        if metric == 'events':
            query = query.order_by(func.count(UsageEvent.id).desc())
        elif metric == 'tokens':
            query = query.order_by(func.sum(UsageEvent.token_count).desc())
        elif metric == 'latency':
            query = query.order_by(func.avg(UsageEvent.latency_ms).desc())

        results = query.limit(limit).all()

        return [
            {
                'user_id': r[0],
                'event_count': r[1],
                'total_tokens': int(r[2] or 0),
                'avg_latency_ms': round(float(r[3] or 0), 2)
            }
            for r in results
        ]

    @staticmethod
    def _to_dict(event: UsageEvent) -> Dict:
        """Convert usage event ORM to dict."""
        if not event:
            return None
        return {
            'id': event.id,
            'user_id': event.user_id,
            'event_type': event.event_type,
            'resource_type': event.resource_type,
            'token_count': event.token_count,
            'latency_ms': event.latency_ms,
            'success': event.success,
            'created_at': event.created_at.isoformat() if event.created_at else None,
        }
