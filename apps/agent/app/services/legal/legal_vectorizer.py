from __future__ import annotations

import os

from app.providers.embedding import EMBEDDING_DIM, get_embedding_provider, vector_literal


def embedding_model_name() -> str:
    if os.getenv("OPENAI_API_KEY"):
        return os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    return f"deterministic-{EMBEDDING_DIM}"


def vectorize_text(text: str) -> tuple[str, str]:
    provider = get_embedding_provider()
    return vector_literal(provider.embed(text)), embedding_model_name()
