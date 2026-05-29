from fastapi import FastAPI

from app.routers.internal import router as internal_router
from app.services.knia.knia_bootstrap import ensure_knia_data_ready

app = FastAPI(title="LawCompass Agent", version="0.1.0")
app.include_router(internal_router)


@app.on_event("startup")
def bootstrap_knia_data() -> None:
    try:
        result = ensure_knia_data_ready()
        print({"event": "knia_bootstrap", **result})
    except Exception as exc:
        print({"event": "knia_bootstrap_failed", "error": str(exc)})
