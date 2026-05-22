from __future__ import annotations

import os

from fastapi import HTTPException


def check_internal_token(token: str | None):
    expected = os.getenv("INTERNAL_SERVICE_TOKEN", "")
    if not token or token != expected:
        raise HTTPException(status_code=401, detail="invalid internal token")
