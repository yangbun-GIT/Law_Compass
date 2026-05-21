#!/usr/bin/env python
from __future__ import annotations

import json

from app.services.legal_api_clients import (
    DATA_GO_TRAFFIC_URL,
    LAW_API_BASE,
    fetch_data_go_traffic,
    fetch_law_search,
    get_external_api_status,
)


def run():
    print("[config]")
    print(f"LAW_API_BASE={LAW_API_BASE}")
    print(f"DATA_GO_TRAFFIC_URL={DATA_GO_TRAFFIC_URL}")
    print()

    print("[test] law.go query='traffic accident'")
    law_rows = fetch_law_search("traffic accident", limit=3)
    print(f"rows={len(law_rows)}")
    if law_rows:
        print(json.dumps(law_rows[0], ensure_ascii=False, indent=2))
    print()

    print("[test] data.go query='rear collision'")
    data_rows = fetch_data_go_traffic("rear collision", limit=3)
    print(f"rows={len(data_rows)}")
    if data_rows:
        print(json.dumps(data_rows[0], ensure_ascii=False, indent=2))
    print()

    print("[status]")
    print(json.dumps(get_external_api_status(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
