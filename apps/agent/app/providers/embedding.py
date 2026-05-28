from __future__ import annotations

import hashlib
import logging
import os
from typing import Protocol

import httpx

EMBEDDING_DIM = 1024
logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]:
        ...


class DeterministicEmbeddingProvider:
    def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        arr = [b / 255 for b in digest]
        while len(arr) < EMBEDDING_DIM:
            arr.extend(arr[: min(len(arr), EMBEDDING_DIM - len(arr))])
        return arr[:EMBEDDING_DIM]


class OpenAIEmbeddingProvider:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.timeout = float(os.getenv("OPENAI_TIMEOUT_SEC", "18"))

    def embed(self, text: str) -> list[float]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is empty")
        payload = {"model": self.model, "input": text[:8000], "dimensions": EMBEDDING_DIM}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post("https://api.openai.com/v1/embeddings", headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status in {401, 403, 429}:
                logger.warning(
                    "OpenAI embedding request failed with recoverable status",
                    extra={"status_code": status, "model": self.model, "api_key_length": len(self.api_key or "")},
                )
            else:
                logger.warning("OpenAI embedding request failed", extra={"status_code": status, "model": self.model})
            raise
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            logger.warning(
                "OpenAI embedding request unavailable",
                extra={"error_type": exc.__class__.__name__, "model": self.model, "api_key_length": len(self.api_key or "")},
            )
            raise
        emb = data["data"][0]["embedding"]
        return [float(x) for x in emb[:EMBEDDING_DIM]]


def get_embedding_provider() -> EmbeddingProvider:
    if os.getenv("OPENAI_API_KEY"):
        return OpenAIEmbeddingProvider()
    return DeterministicEmbeddingProvider()


def vector_literal(values: list[float]) -> str:
    normalized = values[:EMBEDDING_DIM]
    if len(normalized) < EMBEDDING_DIM:
        normalized.extend([0.0] * (EMBEDDING_DIM - len(normalized)))
    return "[" + ",".join(f"{x:.6f}" for x in normalized) + "]"
