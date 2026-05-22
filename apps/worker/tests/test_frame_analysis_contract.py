import tempfile
import unittest
from pathlib import Path

from worker import frame_analysis


class FrameAnalysisContractTest(unittest.TestCase):
    def setUp(self):
        self._enabled = frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS
        self._fixture = frame_analysis.FRAME_ANALYSIS_FIXTURE_MODE
        self._api_key = frame_analysis.OPENAI_API_KEY

    def tearDown(self):
        frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS = self._enabled
        frame_analysis.FRAME_ANALYSIS_FIXTURE_MODE = self._fixture
        frame_analysis.OPENAI_API_KEY = self._api_key

    def test_fixture_mode_returns_contract_observations_without_api_key(self):
        frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS = True
        frame_analysis.FRAME_ANALYSIS_FIXTURE_MODE = "rear_end"
        frame_analysis.OPENAI_API_KEY = ""

        with tempfile.TemporaryDirectory() as tmp:
            frame_path = Path(tmp) / "frame_001.jpg"
            frame_path.write_bytes(b"not-a-real-jpeg-but-exists")

            result = frame_analysis.analyze_frames_with_openai(
                [{"path": str(frame_path), "time_sec": 0.5, "role": "early"}],
                {"upload_id": "upload-1"},
            )

        self.assertTrue(result["enabled"])
        self.assertEqual(result["provider"], "fixture")
        self.assertEqual(result["model"], "fixture:rear_end")
        self.assertEqual(len(result["observations"]), 2)
        self.assertEqual(result["observations"][0]["source"], "frame_analysis:fixture")
        self.assertEqual(result["observations"][0]["frame_refs"], ["frame_001.jpg"])

    def test_enabled_without_key_reports_disabled_reason_when_no_fixture(self):
        frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS = True
        frame_analysis.FRAME_ANALYSIS_FIXTURE_MODE = ""
        frame_analysis.OPENAI_API_KEY = ""

        with tempfile.TemporaryDirectory() as tmp:
            frame_path = Path(tmp) / "frame_001.jpg"
            frame_path.write_bytes(b"exists")
            result = frame_analysis.analyze_frames_with_openai(
                [{"path": str(frame_path), "time_sec": 0.5, "role": "early"}],
                {},
            )

        self.assertFalse(result["enabled"])
        self.assertEqual(result["reason"], "OPENAI_API_KEY is empty")


if __name__ == "__main__":
    unittest.main()
