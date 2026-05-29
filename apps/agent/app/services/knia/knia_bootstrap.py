from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import psycopg

from app.services.knia.knia_json_loader import find_knia_json_path

DB_URL = os.getenv("DATABASE_URL", "postgresql://law:lawpass@postgres:5432/lawcompass")


def ensure_knia_data_ready() -> dict[str, Any]:
    existing = _count_existing_knia_rows()
    if existing > 0:
        return {"status": "ready", "existing_rows": existing, "action": "skip"}

    json_path = find_knia_json_path()
    if json_path:
        result = _run_import_json(json_path)
        return {
            "status": "imported" if result == 0 else "import_failed",
            "json_path": str(json_path),
            "exit_code": result,
        }

    if os.getenv("KNIA_AUTO_COLLECT_ON_START", "0") == "1":
        result = _run_collector()
        return {
            "status": "collected" if result == 0 else "collect_failed",
            "exit_code": result,
        }

    return {
        "status": "missing",
        "action": "none",
        "reason": "KNIA JSON not found and KNIA_AUTO_COLLECT_ON_START is not enabled",
    }


def _count_existing_knia_rows() -> int:
    try:
        with psycopg.connect(DB_URL) as conn, conn.cursor() as cur:
            total = 0
            for table in ("knia_reference_documents", "knia_reference_chunks", "knia_menu_nodes"):
                try:
                    cur.execute(f"SELECT count(*) FROM {table}")
                    total += int(cur.fetchone()[0])
                except Exception:
                    conn.rollback()
            return total
    except Exception:
        return 0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[6]


def _run_import_json(json_path: Path) -> int:
    script = _repo_root() / "apps" / "agent" / "scripts" / "import_knia_fault_ratio_json.py"
    if not script.exists():
        return 2
    proc = subprocess.run(
        [sys.executable, str(script), "--json", str(json_path)],
        cwd=str(_repo_root() / "apps" / "agent"),
        check=False,
    )
    return int(proc.returncode)


def _run_collector() -> int:
    script = _repo_root() / "scripts" / "knia_fault_ratio" / "collect_myaccident_tree.py"
    if not script.exists():
        return 2
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(_repo_root()),
        check=False,
    )
    return int(proc.returncode)
