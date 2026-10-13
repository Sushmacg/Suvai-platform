import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any, Callable, ClassVar

from sqlalchemy.orm import Session

logger = logging.getLogger("suvai.events")


def _jsonable(value: Any) -> Any:
    """Turn event data into plain JSON types (ids and money become strings)."""
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _jsonable(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, (uuid.UUID, Decimal)):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(v) for v in value]
    return value


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base class for events. An event is an immutable fact: ids and plain values only."""

    event_type: ClassVar[str] = "domain_event"

    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def aggregate_id(self) -> uuid.UUID | None:
        """The order / session this event is about. Used to look events up later."""
        return None

    def payload(self) -> dict[str, Any]:
        skip = {"event_id", "occurred_at"}
        return _jsonable(
            {f.name: getattr(self, f.name) for f in fields(self) if f.name not in skip}
        )


Handler = Callable[[Session, Any], None]


@dataclass(frozen=True)
class Subscription:
    name: str
    handler: Handler
    critical: bool


class EventBus:
    """In-process publish/subscribe. Handlers run inside the caller's DB transaction.

    critical=True   -> runs first; if it raises, the error propagates and the
                       publisher rolls everything back (used for stock).
    critical=False  -> runs in a SAVEPOINT; if it raises, only its own changes are
                       undone, the error is logged, and the publisher carries on.
    """

    def __init__(self) -> None:
        self._subscriptions: dict[type[DomainEvent], list[Subscription]] = defaultdict(list)

    def subscribe(
        self,
        event_class: type[DomainEvent],
        handler: Handler,
        *,
        critical: bool = False,
        name: str | None = None,
    ) -> None:
        name = name or f"{handler.__module__}.{handler.__name__}"
        existing = self._subscriptions[event_class]
        if any(s.name == name for s in existing):
            return  # subscribing twice is harmless
        existing.append(Subscription(name=name, handler=handler, critical=critical))

    def unsubscribe(self, event_class: type[DomainEvent], name: str) -> None:
        self._subscriptions[event_class] = [
            s for s in self._subscriptions[event_class] if s.name != name
        ]

    def clear(self) -> None:
        self._subscriptions.clear()

    def publish(self, db: Session, event: DomainEvent) -> None:
        subscriptions = self._subscriptions.get(type(event), [])
        if not subscriptions:
            # A forgotten registration must fail loudly, never silently skip the stock update.
            raise RuntimeError(
                f"No handlers are registered for {event.event_type}. "
                "Call register_event_handlers() at startup."
            )
        for subscription in sorted(subscriptions, key=lambda s: not s.critical):
            if subscription.critical:
                subscription.handler(db, event)
                continue
            try:
                with db.begin_nested():
                    subscription.handler(db, event)
            except Exception:
                logger.exception(
                    "Event handler %s failed for %s; carrying on",
                    subscription.name,
                    event.event_type,
                )

    def describe(self) -> dict[str, list[str]]:
        """The event map: which handlers listen to which event."""
        return {
            event_class.event_type: [
                f"{s.name} ({'critical' if s.critical else 'best-effort'})"
                for s in sorted(subscriptions, key=lambda s: not s.critical)
            ]
            for event_class, subscriptions in self._subscriptions.items()
            if subscriptions
        }


bus = EventBus()
