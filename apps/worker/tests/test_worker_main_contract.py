import unittest

from worker.main import job_timeout_seconds


class WorkerMainContractTest(unittest.TestCase):
    def test_job_timeout_uses_type_specific_preprocess_budget(self):
        self.assertEqual(
            job_timeout_seconds(
                "video_preprocess",
                {"WORKER_JOB_TIMEOUT_SEC": "90", "WORKER_VIDEO_PREPROCESS_TIMEOUT_SEC": "240"},
            ),
            240.0,
        )

    def test_job_timeout_uses_type_specific_analyze_budget(self):
        self.assertEqual(
            job_timeout_seconds(
                "video_analyze",
                {"WORKER_JOB_TIMEOUT_SEC": "90", "WORKER_VIDEO_ANALYZE_TIMEOUT_SEC": "150"},
            ),
            150.0,
        )

    def test_job_timeout_uses_global_budget_with_safe_floor(self):
        self.assertEqual(job_timeout_seconds("video_analyze", {"WORKER_JOB_TIMEOUT_SEC": "20"}), 30.0)
        self.assertEqual(job_timeout_seconds("unknown", {"WORKER_JOB_TIMEOUT_SEC": "180"}), 180.0)

    def test_job_timeout_defaults_to_bounded_runtime(self):
        self.assertEqual(job_timeout_seconds("video_preprocess", {}), 240.0)


if __name__ == "__main__":
    unittest.main()
