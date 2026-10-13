from app.core.events import bus


def register_event_handlers() -> None:
    """The one place that says who listens to what. Safe to call more than once."""
    from app.modules.event_log import handlers as event_log
    from app.modules.inventory import handlers as inventory
    from app.modules.notifications import handlers as notifications
    from app.modules.orders.events import OrderCancelled, OrderCreated
    from app.modules.stalls.events import StallScheduleUpdated

    # Critical: part of the business transaction. If one fails, everything rolls back.
    bus.subscribe(OrderCreated, inventory.reserve_stock_for_order, critical=True)
    bus.subscribe(OrderCancelled, inventory.release_stock_for_order, critical=True)

    # Best-effort: side effects. A failure is logged and the business action still succeeds.
    for event_class in (OrderCreated, OrderCancelled, StallScheduleUpdated):
        bus.subscribe(event_class, event_log.record_event)

    bus.subscribe(OrderCreated, notifications.on_order_created)
    bus.subscribe(OrderCancelled, notifications.on_order_cancelled)
    bus.subscribe(StallScheduleUpdated, notifications.on_stall_schedule_updated)
