from fastapi import APIRouter

from app.core.config import settings

# Every route added here automatically lives under /api/v1
api_router = APIRouter(prefix=settings.API_V1_PREFIX)


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