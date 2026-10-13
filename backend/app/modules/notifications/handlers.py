from sqlalchemy.orm import Session

from app.modules.notifications.service import queue_notification
from app.modules.orders.events import OrderCancelled, OrderCreated
from app.modules.stalls.events import StallScheduleUpdated

STALL_TITLES = {
    "created": "New stall schedule",
    "updated": "Stall schedule changed",
    "opened": "The stall is open",
    "cancelled": "Stall visit cancelled",
    "deleted": "Stall schedule removed",
}


def on_order_created(db: Session, event: OrderCreated) -> None:
    count = sum(line.quantity for line in event.items)
    where = f"{event.location_name} on {event.session_date.isoformat()}"
    queue_notification(
        db,
        event=event,
        audience="user",
        user_id=event.customer_id,
        title="Order placed",
        body=f"We received your order of {count} item(s), Rs. {event.total_amount}. Pick up at {where}.",
    )
    queue_notification(
        db,
        event=event,
        audience="admins",
        title="New order",
        body=f"{event.customer_name} ordered {count} item(s), Rs. {event.total_amount}, for {where}.",
    )


def on_order_cancelled(db: Session, event: OrderCancelled) -> None:
    who = (
        "The stall cancelled your order."
        if event.cancelled_by == "admin"
        else "You cancelled your order."
    )
    queue_notification(
        db,
        event=event,
        audience="user",
        user_id=event.customer_id,
        title="Order cancelled",
        body=f"{who} Reserved items have been returned.",
    )


def on_stall_schedule_updated(db: Session, event: StallScheduleUpdated) -> None:
    title = STALL_TITLES.get(event.change)
    if title is None:
        return  # "closed" is logged for analytics but customers do not need a message
    when = (
        f"{event.session_date.isoformat()}, "
        f"{event.start_time.strftime('%H:%M')} to {event.end_time.strftime('%H:%M')}"
    )
    queue_notification(
        db,
        event=event,
        audience="all_customers",
        title=title,
        body=f"{event.location_name} - {when}",
    )
