from __future__ import annotations
import argparse
from app.services.knia.knia_json_vectorizer import rebuild_knia_json_embeddings

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()
    print(rebuild_knia_json_embeddings(limit=args.limit, force=args.force))
