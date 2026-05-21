from __future__ import annotations
from app.services.knia.knia_json_repository import get_import_stats

stats = get_import_stats()
print(stats)
assert stats["successful_runs"] > 0, "import run success가 없습니다"
assert stats["documents"] > 0, "documents가 없습니다"
assert stats["chunks"] > 0, "chunks가 없습니다"
assert stats["pages"] >= 5, "myaccident pages가 5개 미만입니다"
assert stats["menu_nodes"] > 0, "menu nodes가 없습니다"
print("KNIA JSON import test passed")
