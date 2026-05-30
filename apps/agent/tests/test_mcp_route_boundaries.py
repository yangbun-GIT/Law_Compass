import pytest

from app.routers.internal_routes import cache, knia


@pytest.mark.anyio
async def test_cache_invalidate_uses_tool_executor(monkeypatch):
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "test-token")
    calls = []

    def fake_execute(tool_name, payload, **kwargs):
        calls.append((tool_name, payload, kwargs))
        return {"status": "ok"}

    monkeypatch.setattr(cache, "execute_tool", fake_execute)

    result = await cache.cache_invalidate({"scope": "knia_json"}, x_internal_token="test-token")

    assert result == {"status": "ok"}
    assert calls == [("invalidate_cache_tool", {"scope": "knia_json"}, {"granted_scopes": ["cache.write"]})]


@pytest.mark.anyio
async def test_knia_json_search_uses_tool_executor(monkeypatch):
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "test-token")
    calls = []

    def fake_execute(tool_name, payload, **kwargs):
        calls.append((tool_name, payload, kwargs))
        return {"items": []}

    monkeypatch.setattr(knia, "execute_tool", fake_execute)

    result = await knia.knia_json_search("후방추돌", accidentPartyType="car_vs_car", limit=3, x_internal_token="test-token")

    assert result == {"items": []}
    assert calls == [
        (
            "search_knia_json_rag_tool",
            {"query": "후방추돌", "accident_party_type": "car_vs_car", "limit": 3},
            {"granted_scopes": ["knia.read"]},
        )
    ]


@pytest.mark.anyio
async def test_knia_import_and_menu_read_use_tool_executor(monkeypatch):
    monkeypatch.setenv("INTERNAL_SERVICE_TOKEN", "test-token")
    calls = []

    def fake_execute(tool_name, payload, **kwargs):
        calls.append((tool_name, payload, kwargs))
        return {"status": "ok"}

    monkeypatch.setattr(knia, "execute_tool", fake_execute)

    await knia.knia_import_json({"force": True}, x_internal_token="test-token")
    await knia.knia_myaccident_pages(x_internal_token="test-token")
    await knia.knia_myaccident_tree(2, x_internal_token="test-token")

    assert calls[0] == (
        "import_knia_json_tool",
        {"path": None, "force": True, "rebuild_embeddings": False},
        {"granted_scopes": ["knia.read", "cache.write"]},
    )
    assert calls[1] == ("get_knia_myaccident_pages_tool", {}, {"granted_scopes": ["knia.read"]})
    assert calls[2] == ("get_knia_menu_tree_tool", {"myaccident_no": 2}, {"granted_scopes": ["knia.read"]})
