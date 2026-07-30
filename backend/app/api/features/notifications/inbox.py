"""
Notifications — In-App Inbox (per-user feed)
=============================================
Email subscription management moved here from api/services/notifications.py.

    GET    /notifications/catalog                 — all subscribable event types
    GET    /notifications/subscriptions/me        — current user subscriptions
    POST   /notifications/subscriptions/me        — subscribe
    DELETE /notifications/subscriptions/me/{id}   — unsubscribe
"""
# This module is the authoritative owner of in-app notification routes.
# api/services/notifications.py is now a backward-compat shim.
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_notification_subscription_service
from app.application.email_notifications.catalog import catalog_id_for_routing, list_catalog_entries
from app.application.services.notifications.notification_subscription_service import NotificationSubscriptionService
from app.core.database import get_db
from app.core.security import CurrentUser, require_authenticated_user
from app.core.framework.models.auth import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


class SubscribeBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    catalog_id: str


@router.get("/catalog", name="notification_catalog")
async def get_notification_catalog(_: CurrentUser = Depends(require_authenticated_user)):
    """List all subscribable event types."""
    data = [asdict(e) for e in list_catalog_entries()]
    return {"status": "success", "data": data}


@router.get("/subscriptions/me", name="my_notification_subscriptions")
async def list_my_subscriptions(
    current_user: CurrentUser = Depends(require_authenticated_user),
    service: NotificationSubscriptionService = Depends(get_notification_subscription_service),
):
    """List the current user's active notification subscriptions."""
    rows = await service.list_catalog_subscriptions_for_user(current_user.id)
    out = []
    for r in rows:
        cid = catalog_id_for_routing(r["entity_type"], r["event"])
        out.append({**r, "catalog_id": cid})
    return {"status": "success", "data": out}


@router.post("/subscriptions/me", name="subscribe_notifications")
async def subscribe_me(
    payload: SubscribeBody,
    current_user: CurrentUser = Depends(require_authenticated_user),
    db: AsyncSession = Depends(get_db),
    service: NotificationSubscriptionService = Depends(get_notification_subscription_service),
):
    """Subscribe to a notification event."""
    res = await db.execute(select(User).where(User.id == current_user.id))
    user = res.scalar_one_or_none()
    if not user or not (user.email or "").strip():
        raise HTTPException(status_code=400, detail="User has no email address on file")
    try:
        data = await service.subscribe_by_catalog_id(
            current_user.id, user.email, payload.catalog_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    cid = catalog_id_for_routing(data["entity_type"], data["event"])
    return {"status": "success", "message": "Subscribed", "data": {**data, "catalog_id": cid}}


@router.delete("/subscriptions/me/{subscription_id}", name="unsubscribe_notifications")
async def unsubscribe_me(
    subscription_id: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
    service: NotificationSubscriptionService = Depends(get_notification_subscription_service),
):
    """Unsubscribe from a notification event."""
    ok = await service.unsubscribe(current_user.id, subscription_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"status": "success", "message": "Unsubscribed"}
