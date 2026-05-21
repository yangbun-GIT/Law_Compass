from __future__ import annotations
import argparse
from app.services.knia.knia_json_loader import import_knia_json

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--rebuild-embeddings", action="store_true")
    args = parser.parse_args()
    print(import_knia_json(args.path, force=args.force, rebuild_embeddings=args.rebuild_embeddings))
