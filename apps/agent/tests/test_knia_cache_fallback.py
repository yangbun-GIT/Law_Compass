import os
import unittest
from unittest.mock import patch

from app.services.rag.two_stage_cache import (
    KNIA_JSON_EXACT_CACHE_VERSION,
    get_knia_json_version,
    invalidate_scope,
    search_knia_json_cached,
)


class KniaCacheFallbackTest(unittest.TestCase):
    def test_knia_json_cache_degrades_without_database_url(self):
        with patch.dict(os.environ, {"DATABASE_URL": ""}, clear=False):
            result = search_knia_json_cached("정차 중 후방 추돌", accident_party_type="car_vs_car", scenario_type="rear_end_collision")
            version = get_knia_json_version()

        self.assertEqual(version, "dev")
        self.assertEqual(result["items"], [])
        self.assertFalse(result["cache"]["exact_hit"])
        self.assertFalse(result["cache"]["semantic_hit"])
        self.assertEqual(result["cache"]["disabled_reason"], "DATABASE_URL missing")
        self.assertIn(f"knia_json:exact:{KNIA_JSON_EXACT_CACHE_VERSION}:dev:car_vs_car:rear_end_collision:", result["cache"]["key"])
        self.assertEqual(result["cache"]["scenario_type"], "rear_end_collision")

    def test_knia_json_cache_invalidation_reports_disabled_without_database_url(self):
        with patch.dict(os.environ, {"DATABASE_URL": ""}, clear=False):
            result = invalidate_scope("knia_json")

        self.assertEqual(result["scope"], "knia_json")
        self.assertEqual(result["semantic_cache_deleted"], 0)
        self.assertEqual(result["disabled_reason"], "DATABASE_URL missing")

    def test_knia_json_semantic_lookup_is_scoped_by_scenario_type(self):
        executed = []

        class Cursor:
            def execute(self, sql, params=None):
                executed.append((sql, params))
            def fetchone(self):
                return None
            def fetchall(self):
                return []
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        class Conn:
            def cursor(self):
                return Cursor()
            def commit(self):
                return None
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        class Provider:
            def embed(self, _text):
                return [0.01, 0.02, 0.03]

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://test"}, clear=False), \
            patch("app.services.rag.two_stage_cache.get_knia_json_version", return_value="fixture"), \
            patch("app.services.rag.two_stage_cache._redis", return_value=None), \
            patch("app.services.rag.two_stage_cache.get_embedding_provider", return_value=Provider()), \
            patch("app.services.rag.two_stage_cache.vector_literal", return_value="'[0.01,0.02,0.03]'"), \
            patch("app.services.rag.two_stage_cache.psycopg.connect", return_value=Conn()):
            result = search_knia_json_cached(
                "후미추돌 정차 신호대기 뒤차 안전거리",
                accident_party_type="car_vs_car",
                scenario_type="rear_end_collision",
            )

        semantic_sql, semantic_params = executed[0]
        self.assertIn("coalesce(scenario_type,'unknown')=%s", semantic_sql)
        self.assertIn("rear_end_collision", semantic_params)
        self.assertFalse(result["cache"]["semantic_hit"])
        self.assertEqual(result["cache"]["scenario_type"], "rear_end_collision")


if __name__ == "__main__":
    unittest.main()
