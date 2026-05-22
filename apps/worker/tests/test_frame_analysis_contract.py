import tempfile
import unittest
from pathlib import Path

from worker import frame_analysis


class FrameAnalysisContractTest(unittest.TestCase):
    def setUp(self):
        self._enabled = frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS
        self._fixture = frame_analysis.FRAME_ANALYSIS_FIXTURE_MODE
        self._api_key = frame_analysis.OPENAI_API_KEY
        self._model = frame_analysis.OPENAI_VISION_MODEL
        self._max_output_tokens = frame_analysis.OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS
        self._post_json = frame_analysis._post_json

    def tearDown(self):
        frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS = self._enabled
        frame_analysis.FRAME_ANALYSIS_FIXTURE_MODE = self._fixture
        frame_analysis.OPENAI_API_KEY = self._api_key
        frame_analysis.OPENAI_VISION_MODEL = self._model
        frame_analysis.OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS = self._max_output_tokens
        frame_analysis._post_json = self._post_json

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
        self.assertEqual(result["observations"][0]["observation_quality"]["frame_ref_count"], 1)
        self.assertEqual(result["observation_quality_summary"]["single_frame_observation_count"], 2)

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

    def test_held_quality_fixture_returns_low_confidence_observation(self):
        frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS = True
        frame_analysis.FRAME_ANALYSIS_FIXTURE_MODE = "held_quality"
        frame_analysis.OPENAI_API_KEY = ""

        with tempfile.TemporaryDirectory() as tmp:
            frame_path = Path(tmp) / "frame_001.jpg"
            frame_path.write_bytes(b"exists")
            result = frame_analysis.analyze_frames_with_openai(
                [{"path": str(frame_path), "time_sec": 0.5, "role": "early"}],
                {"upload_id": "upload-held"},
            )

        self.assertTrue(result["enabled"])
        self.assertEqual(result["model"], "fixture:held_quality")
        self.assertEqual(result["observations"][0]["field"], "turn_signal")
        self.assertEqual(result["observations"][0]["observation_quality"]["level"], "none")
        self.assertEqual(result["observation_quality_summary"]["quality_counts"]["none"], 1)

    def test_openai_frame_selection_keeps_context_and_middle_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 13):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({"path": str(frame_path), "time_sec": index * 0.5, "role": "time_sequence"})

            selected = frame_analysis._select_openai_frames(frames, 6)

        refs = [Path(frame["path"]).name for frame in selected]
        self.assertEqual(refs, [
            "frame_001.jpg",
            "frame_005.jpg",
            "frame_006.jpg",
            "frame_007.jpg",
            "frame_008.jpg",
            "frame_012.jpg",
        ])

    def test_gpt5_payload_uses_cost_controls_without_temperature(self):
        captured = {}

        def fake_post_json(url, payload, headers=None, timeout=25):
            captured["url"] = url
            captured["payload"] = payload
            return {
                "id": "resp_123",
                "output_text": (
                    '{"summary":"frames analyzed","observations":['
                    '{"field":"stopped","value":true,"confidence":0.81,'
                    '"frame_refs":["frame_001.jpg"],"reason":"visible stationary position"}]}'
                ),
            }

        frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS = True
        frame_analysis.FRAME_ANALYSIS_FIXTURE_MODE = ""
        frame_analysis.OPENAI_API_KEY = "test-key"
        frame_analysis.OPENAI_VISION_MODEL = "gpt-5-nano"
        frame_analysis.OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS = 900
        frame_analysis._post_json = fake_post_json

        with tempfile.TemporaryDirectory() as tmp:
            frame_path = Path(tmp) / "frame_001.jpg"
            frame_path.write_bytes(b"exists")
            result = frame_analysis.analyze_frames_with_openai(
                [{"path": str(frame_path), "time_sec": 0.5, "role": "early"}],
                {},
            )

        payload = captured["payload"]
        self.assertTrue(result["enabled"])
        self.assertEqual(payload["model"], "gpt-5-nano")
        self.assertEqual(payload["max_output_tokens"], 900)
        self.assertFalse(payload["store"])
        self.assertEqual(payload["text"]["verbosity"], "low")
        self.assertEqual(payload["reasoning"]["effort"], "minimal")
        self.assertNotIn("temperature", payload)
        self.assertEqual(result["observation_quality_summary"]["observation_count"], 1)
        self.assertEqual(result["observations"][0]["observation_quality"]["level"], "low")

    def test_non_gpt5_payload_uses_temperature_zero(self):
        self.assertEqual(frame_analysis._generation_controls_for_model("gpt-4.1-mini"), {"temperature": 0})
        self.assertNotIn("verbosity", frame_analysis._text_options_for_model("gpt-4.1-mini"))

    def test_prompt_and_confidence_gate_reduce_negative_stopped_false_positives(self):
        captured = {}

        def fake_post_json(url, payload, headers=None, timeout=25):
            captured["payload"] = payload
            return {
                "id": "resp_stopped_false",
                "output_text": (
                    '{"observations":['
                    '{"field":"stopped","value":false,"confidence":0.95,'
                    '"frame_refs":["frame_001.jpg","frame_002.jpg","frame_003.jpg"],'
                    '"reason":"dashcam scene changes across frames"}]}'
                ),
            }

        frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS = True
        frame_analysis.FRAME_ANALYSIS_FIXTURE_MODE = ""
        frame_analysis.OPENAI_API_KEY = "test-key"
        frame_analysis.OPENAI_VISION_MODEL = "gpt-4.1-mini"
        frame_analysis._post_json = fake_post_json

        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 4):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({"path": str(frame_path), "time_sec": index, "role": "time_sequence"})
            result = frame_analysis.analyze_frames_with_openai(frames, {})

        prompt_text = captured["payload"]["input"][0]["content"][0]["text"]
        self.assertIn("Do not mark stopped=false merely because the dashcam image changes", prompt_text)
        self.assertEqual(result["observations"][0]["field"], "stopped")
        self.assertEqual(result["observations"][0]["value"], False)
        self.assertEqual(result["observations"][0]["confidence"], 0.81)
        self.assertEqual(result["observations"][0]["observation_quality"]["level"], "low")


if __name__ == "__main__":
    unittest.main()
