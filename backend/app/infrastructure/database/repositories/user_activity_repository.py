"""
User Activity Repository
=======================
Repository for tracking and retrieving user activity data for personalized home page.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import and_, or_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.framework.models.infrastructure import UserActivity
from app.core.framework.models.auth import User


class UserActivityRepository:
    """Repository for user activity tracking and retrieval."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_activity(
        self,
        user_id: str,
        username: str,
        activity_type: str,
        entity_name: Optional[str] = None,
        page_path: Optional[str] = None,
        page_label: Optional[str] = None,
    ) -> UserActivity:
        """
        Record or update a user activity.
        
        Uses upsert logic: if activity exists, increment visit count and update score;
        otherwise create new activity record.
        
        Score calculation:
        - Base score: 1.0
        - Visit count multiplier: 1 + (visit_count * 0.1)
        - Recency bonus: activities within last 7 days get 2x multiplier
        """
        # Try to find existing activity
        result = await self.db.execute(
            select(UserActivity).where(
                and_(
                    UserActivity.user_id == user_id,
                    UserActivity.activity_type == activity_type,
                    UserActivity.entity_name == entity_name if entity_name else True,
                    UserActivity.page_path == page_path if page_path else True,
                )
            )
        )
        existing = result.scalar_one_or_none()

        now = datetime.utcnow()

        if existing:
            # Update existing activity
            existing.visit_count += 1
            existing.last_visited_at = now
            existing.updated_at = now
            
            # Recalculate score with recency bonus
            days_since_last_visit = (now - existing.last_visited_at).days
            recency_multiplier = 2.0 if days_since_last_visit <= 7 else 1.0
            existing.score = (1.0 + (existing.visit_count * 0.1)) * recency_multiplier
            
            await self.db.flush()
            return existing
        else:
            # Create new activity
            activity = UserActivity(
                user_id=user_id,
                username=username,
                activity_type=activity_type,
                entity_name=entity_name,
                page_path=page_path,
                page_label=page_label,
                visit_count=1,
                score=1.0,
                last_visited_at=now,
                created_at=now,
                updated_at=now,
            )
            self.db.add(activity)
            await self.db.flush()
            return activity

    async def get_user_activities(
        self,
        user_id: str,
        activity_type: Optional[str] = None,
        limit: int = 10,
        days_ago: Optional[int] = 30,
    ) -> List[UserActivity]:
        """
        Get user's activities ranked by score.
        
        Args:
            user_id: User ID
            activity_type: Filter by activity type (optional)
            limit: Maximum number of results
            days_ago: Only include activities from last N days (None for all time)
        """
        filters = [UserActivity.user_id == user_id]
        
        if activity_type:
            filters.append(UserActivity.activity_type == activity_type)
        
        if days_ago is not None:
            cutoff_date = datetime.utcnow() - timedelta(days=days_ago)
            filters.append(UserActivity.last_visited_at >= cutoff_date)

        result = await self.db.execute(
            select(UserActivity)
            .where(and_(*filters))
            .order_by(desc(UserActivity.score), desc(UserActivity.last_visited_at))
            .limit(limit)
        )
        return result.scalars().all()

    async def get_frequent_entities(
        self,
        user_id: str,
        limit: int = 5,
        days_ago: int = 30,
    ) -> List[dict]:
        """
        Get user's most frequently accessed entities.
        
        Returns a list of dicts with entity_name, page_label, visit_count, score.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_ago)
        
        result = await self.db.execute(
            select(
                UserActivity.entity_name,
                UserActivity.page_label,
                func.sum(UserActivity.visit_count).label("total_visits"),
                func.max(UserActivity.score).label("max_score"),
                func.max(UserActivity.last_visited_at).label("last_visited"),
            )
            .where(
                and_(
                    UserActivity.user_id == user_id,
                    UserActivity.activity_type == "entity_view",
                    UserActivity.entity_name.isnot(None),
                    UserActivity.last_visited_at >= cutoff_date,
                )
            )
            .group_by(UserActivity.entity_name, UserActivity.page_label)
            .order_by(desc("max_score"), desc("total_visits"))
            .limit(limit)
        )
        
        activities = []
        for row in result:
            activities.append({
                "entity_name": row.entity_name,
                "page_label": row.page_label or row.entity_name,
                "visit_count": row.total_visits,
                "score": row.max_score,
                "last_visited": row.last_visited,
            })
        
        return activities

    async def get_frequent_pages(
        self,
        user_id: str,
        limit: int = 5,
        days_ago: int = 30,
    ) -> List[dict]:
        """
        Get user's most frequently visited pages (non-entity pages).
        
        Returns a list of dicts with page_path, page_label, visit_count, score.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_ago)
        
        result = await self.db.execute(
            select(
                UserActivity.page_path,
                UserActivity.page_label,
                func.sum(UserActivity.visit_count).label("total_visits"),
                func.max(UserActivity.score).label("max_score"),
                func.max(UserActivity.last_visited_at).label("last_visited"),
            )
            .where(
                and_(
                    UserActivity.user_id == user_id,
                    UserActivity.activity_type == "page_visit",
                    UserActivity.page_path.isnot(None),
                    UserActivity.last_visited_at >= cutoff_date,
                )
            )
            .group_by(UserActivity.page_path, UserActivity.page_label)
            .order_by(desc("max_score"), desc("total_visits"))
            .limit(limit)
        )
        
        activities = []
        for row in result:
            activities.append({
                "page_path": row.page_path,
                "page_label": row.page_label or row.page_path,
                "visit_count": row.total_visits,
                "score": row.max_score,
                "last_visited": row.last_visited,
            })
        
        return activities

    async def cleanup_old_activities(self, days_to_keep: int = 90) -> int:
        """
        Delete activities older than specified days.
        
        Returns the number of deleted records.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        result = await self.db.execute(
            select(UserActivity.id).where(UserActivity.last_visited_at < cutoff_date)
        )
        ids_to_delete = result.scalars().all()
        
        if ids_to_delete:
            await self.db.execute(
                select(UserActivity).where(UserActivity.id.in_(ids_to_delete))
            )
            for activity in (await self.db.execute(
                select(UserActivity).where(UserActivity.id.in_(ids_to_delete))
            )).scalars().all():
                await self.db.delete(activity)
        
        return len(ids_to_delete)
