from __future__ import annotations
from app.services.knia.knia_json_menu_builder import get_myaccident_tree

for no in range(1, 6):
    result = get_myaccident_tree(no)
    page = result.get("page")
    tree = result.get("tree") or []
    print({"myaccident_no": no, "page": page and page.get("page_title"), "top_nodes": len(tree)})
    assert page, f"myaccident{no} page가 없습니다"
    assert tree, f"myaccident{no} tree가 비었습니다"
    def walk(nodes):
        for n in nodes:
            yield n
            yield from walk(n.get("children") or [])
    flat = list(walk(tree))
    print(" nodes", len(flat), "charts", sum(1 for x in flat if x.get("chart_no")))
    assert len(flat) > 0
print("KNIA menu tree test passed")
