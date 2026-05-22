from __future__ import annotations

from fastapi import APIRouter

from app.routers.internal_routes import (
    analysis_router,
    cache_router,
    chat_router,
    health_router,
    jobs_router,
    knia_router,
    legal_router,
)

router = APIRouter(prefix="/internal/v1", tags=["internal"])

router.include_router(health_router)
router.include_router(analysis_router)
router.include_router(jobs_router)
router.include_router(legal_router)
router.include_router(chat_router)
router.include_router(knia_router)
router.include_router(cache_router)
