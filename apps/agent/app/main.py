from fastapi import FastAPI
from app.routers.internal import router as internal_router

app = FastAPI(title="LawCompass Agent", version="0.1.0")
app.include_router(internal_router)

