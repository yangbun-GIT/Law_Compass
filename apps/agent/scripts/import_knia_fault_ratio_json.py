from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

AGENT_ROOT = Path(__file__).resolve().parents[1]
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from app.services.knia.knia_json_loader import import_knia_json


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--rebuild-embeddings", action="store_true")
    args = parser.parse_args()
    result = import_knia_json(args.path, force=args.force, rebuild_embeddings=args.rebuild_embeddings)
    summary_keys = [
        "charts_total",
        "charts_imported",
        "charts_review_required",
        "rag_documents_total",
        "rag_documents_imported",
        "skipped_count",
        "validation_warnings_count",
    ]
    print(json.dumps({key: result.get(key, 0) for key in summary_keys}, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
