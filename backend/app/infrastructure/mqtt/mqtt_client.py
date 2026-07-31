"""
MQTT Weight Reader Subscriber
=============================
Subscribes to MQTT wildcard ``#``, filters for ``{device_id}/weight`` topics,
and processes each weight reading through the full pipeline:

1. Match CrateClass by weight range
2. Find or create Order for that class
3. Find or create Crate for that order
4. Validate weight → create Reading
5. Update counts on crate + order
6. Emit Socket.IO events
7. Publish response to ``{device_id}/data``
"""

import asyncio
import logging
import uuid
from datetime import datetime

import aiomqtt
from sqlalchemy import select, and_

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.serialization import record_to_dict
from app.modules.warehouse.models.crate import Crate
from app.modules.warehouse.models.crate_class import CrateClass
from app.modules.warehouse.models.order import Order
from app.modules.warehouse.models.reading import Reading
from app.application.services.notifications.socketio import socket_manager

logger = logging.getLogger(__name__)

# ── helpers ──────────────────────────────────────────────────────────────────


def _short_id(prefix: str) -> str:
    """Generate a short unique ID like ``ORD-A3F8B2C1``."""
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


# ── subscriber ───────────────────────────────────────────────────────────────


class MqttWeightSubscriber:
    """Background subscriber that listens for ESP32 weight readings via MQTT.

    Lifecycle::

        subscriber = MqttWeightSubscriber()
        await subscriber.start()   # connects + launches background task
        ...
        await subscriber.stop()    # cancels task + disconnects
    """

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None

    # ── lifecycle ────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Connect to the MQTT broker and begin the processing loop."""
        if self._task is not None:
            return

        logger.info(
            "Starting MQTT subscriber — broker %s:%s",
            settings.MQTT_BROKER_HOST,
            settings.MQTT_BROKER_PORT,
        )
        self._task = asyncio.create_task(self._process_loop())

    async def stop(self) -> None:
        """Cancel the processing loop and disconnect."""
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        logger.info("MQTT subscriber stopped.")

    # ── main loop ────────────────────────────────────────────────────────

    async def _process_loop(self) -> None:
        """Reconnection loop around the MQTT message iterator."""
        while True:
            try:
                async with aiomqtt.Client(
                    hostname=settings.MQTT_BROKER_HOST,
                    port=settings.MQTT_BROKER_PORT,
                    username=settings.MQTT_BROKER_USERNAME or None,
                    password=settings.MQTT_BROKER_PASSWORD or None,
                ) as client:
                    await client.subscribe("#")
                    logger.info("MQTT connected — subscribed to '#'")

                    async for message in client.messages:
                        await self._handle_message(message)

            except aiomqtt.MqttError as exc:
                logger.error("MQTT error: %s — reconnecting in 5 s …", exc)
                await asyncio.sleep(5)

    # ── message dispatch ─────────────────────────────────────────────────

    async def _handle_message(self, message: aiomqtt.Message) -> None:
        """Parse and dispatch an incoming MQTT message."""
        topic = str(message.topic)
        parts = topic.split("/")

        # Only process topics matching {device_id}/weight
        if len(parts) < 2 or parts[1] != "weight":
            return

        device_id = parts[0]

        try:
            weight_grams = float(message.payload)
        except (ValueError, TypeError):
            logger.warning("Invalid weight payload from %s: %s", device_id, message.payload)
            await self._publish(device_id, f"Error: invalid weight '{message.payload!r}'")
            return

        logger.info("Received %.1f g from device %s", weight_grams, device_id)
        await self._handle_weight(device_id, weight_grams)

    # ── core pipeline ────────────────────────────────────────────────────

    async def _handle_weight(self, device_id: str, weight_grams: float) -> None:
        """Full processing pipeline for a single weight reading."""
        async with async_session_maker() as db:
            try:
                # 1. Match CrateClass by weight range
                crate_class = await self._match_crate_class(db, weight_grams)
                if crate_class is None:
                    msg = f"Unknown: no class for {weight_grams:.0f}g"
                    logger.warning(msg)
                    await self._publish(device_id, msg)
                    return

                # 2. Find or create Order for this class
                order = await self._find_or_create_order(db, crate_class)

                # 3. Find or create Crate for this order
                crate = await self._find_or_create_crate(db, order, crate_class)

                # 4. Validate weight against class range
                valid = self._is_valid_weight(weight_grams, crate_class)

                # 5. Create Reading
                reading = Reading(
                    id=_short_id("RDG"),
                    crate=crate.id,
                    order=order.id,
                    weight_grams=weight_grams,
                    recorded_at=datetime.utcnow(),
                    valid=valid,
                )
                db.add(reading)

                # 6. Update counts
                crate.counted = (crate.counted or 0.0) + 1
                order.current_amount = (order.current_amount or 0.0) + weight_grams

                await db.commit()
                await db.refresh(reading)

                logger.info(
                    "Reading %s created — %.1fg | valid=%s | class=%s | order=%s | crate=%s",
                    reading.id,
                    weight_grams,
                    valid,
                    crate_class.name,
                    order.id,
                    crate.id,
                )

                # 7. Emit Socket.IO events
                await self._emit_events(reading, crate, order, db)

                # 8. Publish response to ESP32
                response = f"{crate_class.name}: {order.id}/{crate.id}"
                await self._publish(device_id, response)

            except Exception as exc:
                logger.exception("Failed to process weight %.1fg from %s", weight_grams, device_id)
                await db.rollback()
                await self._publish(device_id, f"Error: {exc}")

    # ── database helpers ─────────────────────────────────────────────────

    @staticmethod
    async def _match_crate_class(db, weight: float) -> CrateClass | None:
        """Find the CrateClass whose range contains *weight*.

        When multiple classes match, the one with the **narrowest** range wins.
        """
        result = await db.execute(
            select(CrateClass).where(
                and_(
                    CrateClass.min_weight <= weight,
                    CrateClass.max_weight >= weight,
                )
            )
        )
        matches: list[CrateClass] = list(result.scalars().all())

        if not matches:
            return None

        # Pick the narrowest range (tightest fit)
        matches.sort(key=lambda cc: (cc.max_weight or 0) - (cc.min_weight or 0))
        return matches[0]

    @staticmethod
    async def _find_or_create_order(db, crate_class: CrateClass) -> Order:
        """Return the oldest active Order for *crate_class*, or create one."""
        result = await db.execute(
            select(Order)
            .where(
                and_(
                    Order.crate_class == crate_class.id,
                    Order.status.in_(["pending", "in-progress"]),
                )
            )
            .order_by(Order.created_at.asc())
            .limit(1)
        )
        order = result.scalar_one_or_none()

        if order is not None:
            return order

        # Auto-create
        order = Order(
            id=_short_id("ORD"),
            crate_class=crate_class.id,
            total_amount=0.0,
            current_amount=0.0,
            status="in-progress",
        )
        db.add(order)
        await db.flush()
        logger.info("Auto-created order %s for class %s", order.id, crate_class.name)
        return order

    @staticmethod
    async def _find_or_create_crate(db, order: Order, crate_class: CrateClass) -> Crate:
        """Return the first Crate with spare capacity, or create one."""
        result = await db.execute(
            select(Crate)
            .where(
                and_(
                    Crate.order == order.id,
                    Crate.counted < Crate.target,
                )
            )
            .limit(1)
        )
        crate = result.scalar_one_or_none()

        if crate is not None:
            return crate

        # Auto-create with a default target of 50 mangoes
        crate_id = _short_id("CRT")
        crate = Crate(
            id=crate_id,
            code=crate_id,  # unique crate code
            order=order.id,
            crate_class=crate_class.id,
            target=50.0,
            counted=0.0,
        )
        db.add(crate)
        await db.flush()
        logger.info("Auto-created crate %s for order %s", crate.id, order.id)
        return crate

    @staticmethod
    def _is_valid_weight(weight: float, crate_class: CrateClass) -> bool:
        """Check whether *weight* falls within the class range."""
        lo = crate_class.min_weight
        hi = crate_class.max_weight
        if lo is None or hi is None:
            return True  # no range defined — accept everything
        return lo <= weight <= hi

    # ── Socket.IO ────────────────────────────────────────────────────────

    @staticmethod
    async def _emit_events(reading: Reading, crate: Crate, order: Order, db) -> None:
        """Emit ``entity:change`` events for the new reading and updated related records."""
        try:
            reading_dict = record_to_dict(reading)
            crate_dict = record_to_dict(crate)
            order_dict = record_to_dict(order)

            await socket_manager.emit_created("reading", reading_dict)
            await socket_manager.emit_updated("crate", crate_dict)
            await socket_manager.emit_updated("order", order_dict)
        except Exception:
            logger.exception("Socket.IO emission failed — non-fatal")

    # ── MQTT response ────────────────────────────────────────────────────

    async def _publish(self, device_id: str, payload: str) -> None:
        """Publish a response string to ``{device_id}/data``."""
        topic = f"{device_id}/data"
        try:
            async with aiomqtt.Client(
                hostname=settings.MQTT_BROKER_HOST,
                port=settings.MQTT_BROKER_PORT,
                username=settings.MQTT_BROKER_USERNAME or None,
                password=settings.MQTT_BROKER_PASSWORD or None,
            ) as client:
                await client.publish(topic, payload.encode(), qos=1)
            logger.debug("Published to %s → %s", topic, payload)
        except Exception:
            logger.exception("Failed to publish response to %s", topic)
