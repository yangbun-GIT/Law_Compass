from .analysis import router as analysis_router
from .cache import router as cache_router
from .chat import router as chat_router
from .health import router as health_router
from .jobs import router as jobs_router
from .knia import router as knia_router
from .legal import router as legal_router
from .mobile_demo import router as mobile_demo_router

__all__ = [
    "analysis_router",
    "cache_router",
    "chat_router",
    "health_router",
    "jobs_router",
    "knia_router",
    "legal_router",
    "mobile_demo_router",
]
