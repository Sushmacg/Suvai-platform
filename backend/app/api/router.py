from fastapi import APIRouter

from app.core.config import settings
from app.modules.auth.router import router as auth_router
from app.modules.users.router import router as users_router
from app.modules.products.router import router as products_router
from app.modules.stalls.router import router as stalls_router
from app.modules.inventory.router import router as inventory_router
from app.modules.orders.router import router as orders_router
from app.modules.expenses.router import router as expenses_router
from app.modules.reviews.router import router as reviews_router
from app.modules.event_log.router import router as event_log_router
from app.modules.notifications.router import router as notifications_router

from app.modules.forecasts.router import router as forecasts_router
from app.ai.router import router as assistant_router

api_router = APIRouter(prefix=settings.API_V1_PREFIX)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(products_router)
api_router.include_router(stalls_router)
api_router.include_router(inventory_router)
api_router.include_router(orders_router)
api_router.include_router(expenses_router)
api_router.include_router(reviews_router)
api_router.include_router(event_log_router)
api_router.include_router(notifications_router)



@api_router.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Later, module routers get included here, for example:
# api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
from app.modules.analytics.router import router as analytics_router
api_router.include_router(analytics_router)
api_router.include_router(forecasts_router)
api_router.include_router(assistant_router)
