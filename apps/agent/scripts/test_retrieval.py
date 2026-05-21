#!/usr/bin/env python
from __future__ import annotations

import json
import sys

from app.services.rag_client import retrieve_kb


def run():
    query = " ".join(sys.argv[1:]) or "rear collision safe distance insurance report"
    rows = retrieve_kb(query, limit=5)
    print(f"query={query}")
    print(f"rows={len(rows)}")
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
