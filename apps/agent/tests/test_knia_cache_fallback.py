import os
import unittest
from unittest.mock import patch

from app.services.rag.two_stage_cache import get_knia_json_version, invalidate_scope, search_knia_json_cached


class KniaCacheFallbackTest(unittest.TestCase):
    def test_knia_json_cache_degrades_without_database_url(self):
        with patch.dict(os.environ, {"DATABASE_URL": ""}, clear=False):
            result = search_knia_json_cached("정차 중 후방 추돌", accident_party_type="car_vs_car")
            version = get_knia_json_version()

        self.assertEqual(version, "dev")
        self.assertEqual(result["items"], [])
        self.assertFalse(result["cache"]["exact_hit"])
        self.assertFalse(result["cache"]["semantic_hit"])
        self.assertEqual(result["cache"]["disabled_reason"], "DATABASE_URL missing")

    def test_knia_json_cache_invalidation_reports_disabled_without_database_url(self):
        with patch.dict(os.environ, {"DATABASE_URL": ""}, clear=False):
            result = invalidate_scope("knia_json")

        self.assertEqual(result["scope"], "knia_json")
        self.assertEqual(result["semantic_cache_deleted"], 0)
        self.assertEqual(result["disabled_reason"], "DATABASE_URL missing")


if __name__ == "__main__":
    unittest.main()
