import json
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
        self._retry_model = frame_analysis.OPENAI_FRAME_ANALYSIS_RETRY_MODEL
        self._max_frames = frame_analysis.OPENAI_FRAME_ANALYSIS_MAX_FRAMES
        self._max_output_tokens = frame_analysis.OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS
        self._zero_observation_retry = frame_analysis.OPENAI_FRAME_ANALYSIS_ZERO_OBSERVATION_RETRY
        self._target_retry = frame_analysis.OPENAI_FRAME_ANALYSIS_TARGET_RETRY
        self._ambiguous_target_retry = frame_analysis.OPENAI_FRAME_ANALYSIS_AMBIGUOUS_TARGET_RETRY
        self._retry_min_frames = frame_analysis.OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES
        self._error_retry = frame_analysis.OPENAI_FRAME_ANALYSIS_ERROR_RETRY
        self._target_retry_crops = frame_analysis.OPENAI_FRAME_ANALYSIS_TARGET_RETRY_CROPS
        self._target_retry_enhance = frame_analysis.OPENAI_FRAME_ANALYSIS_TARGET_RETRY_ENHANCE
        self._target_retry_max_crops = frame_analysis.OPENAI_FRAME_ANALYSIS_TARGET_RETRY_MAX_CROPS
        self._post_json = frame_analysis._post_json

    def tearDown(self):
        frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS = self._enabled
        frame_analysis.FRAME_ANALYSIS_FIXTURE_MODE = self._fixture
        frame_analysis.OPENAI_API_KEY = self._api_key
        frame_analysis.OPENAI_VISION_MODEL = self._model
        frame_analysis.OPENAI_FRAME_ANALYSIS_RETRY_MODEL = self._retry_model
        frame_analysis.OPENAI_FRAME_ANALYSIS_MAX_FRAMES = self._max_frames
        frame_analysis.OPENAI_FRAME_ANALYSIS_MAX_OUTPUT_TOKENS = self._max_output_tokens
        frame_analysis.OPENAI_FRAME_ANALYSIS_ZERO_OBSERVATION_RETRY = self._zero_observation_retry
        frame_analysis.OPENAI_FRAME_ANALYSIS_TARGET_RETRY = self._target_retry
        frame_analysis.OPENAI_FRAME_ANALYSIS_AMBIGUOUS_TARGET_RETRY = self._ambiguous_target_retry
        frame_analysis.OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES = self._retry_min_frames
        frame_analysis.OPENAI_FRAME_ANALYSIS_ERROR_RETRY = self._error_retry
        frame_analysis.OPENAI_FRAME_ANALYSIS_TARGET_RETRY_CROPS = self._target_retry_crops
        frame_analysis.OPENAI_FRAME_ANALYSIS_TARGET_RETRY_ENHANCE = self._target_retry_enhance
        frame_analysis.OPENAI_FRAME_ANALYSIS_TARGET_RETRY_MAX_CROPS = self._target_retry_max_crops
        frame_analysis._post_json = self._post_json

    def test_disabled_mode_reports_available_frames_without_analysis(self):
        frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS = False

        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 4):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({"path": str(frame_path), "time_sec": index, "role": "time_sequence"})
            result = frame_analysis.analyze_frames_with_openai(frames, {})

        self.assertFalse(result["enabled"])
        self.assertEqual(result["available_frame_count"], 3)
        self.assertEqual(result["selected_frame_count"], 0)
        self.assertEqual(result["frame_selection_strategy"], frame_analysis.FRAME_SELECTION_STRATEGY)

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
        self.assertEqual(result["frame_selection_strategy"], frame_analysis.FRAME_SELECTION_STRATEGY)
        self.assertEqual(result["available_frame_count"], 1)
        self.assertEqual(result["selected_frame_count"], 1)

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

    def test_conflict_stopped_fixture_returns_override_quality_observation(self):
        frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS = True
        frame_analysis.FRAME_ANALYSIS_FIXTURE_MODE = "conflict_stopped"
        frame_analysis.OPENAI_API_KEY = ""

        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 3):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({"path": str(frame_path), "time_sec": index * 0.5, "role": "time_sequence"})
            result = frame_analysis.analyze_frames_with_openai(frames, {"upload_id": "upload-conflict"})

        observation = result["observations"][0]
        self.assertEqual(result["model"], "fixture:conflict_stopped")
        self.assertEqual(observation["field"], "stopped")
        self.assertEqual(observation["value"], False)
        self.assertEqual(observation["confidence"], 0.93)
        self.assertEqual(observation["frame_refs"], ["frame_001.jpg", "frame_002.jpg"])
        self.assertEqual(observation["observation_quality"]["level"], "high")
        self.assertEqual(result["observation_quality_summary"]["multi_frame_observation_count"], 1)

    def test_openai_frame_selection_keeps_context_and_middle_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 13):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({"path": str(frame_path), "time_sec": index * 0.5, "role": "time_sequence"})

            selected = frame_analysis._select_openai_frames(frames, 6)
            metadata = frame_analysis._frame_selection_metadata(frames, selected)

        refs = [Path(frame["path"]).name for frame in selected]
        self.assertEqual(refs, [
            "frame_001.jpg",
            "frame_005.jpg",
            "frame_006.jpg",
            "frame_007.jpg",
            "frame_008.jpg",
            "frame_012.jpg",
        ])
        self.assertEqual(metadata["frame_selection_strategy"], frame_analysis.FRAME_SELECTION_STRATEGY)
        self.assertEqual(metadata["available_frame_count"], 12)
        self.assertEqual(metadata["selected_frame_count"], 6)

    def test_default_openai_frame_budget_can_cover_more_short_accident_context(self):
        frame_analysis.OPENAI_FRAME_ANALYSIS_MAX_FRAMES = 10

        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 13):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({"path": str(frame_path), "time_sec": index * 0.5, "role": "time_sequence"})

            selected = frame_analysis._select_openai_frames(
                frames,
                frame_analysis.OPENAI_FRAME_ANALYSIS_MAX_FRAMES,
            )
            metadata = frame_analysis._frame_selection_metadata(frames, selected)

        refs = [Path(frame["path"]).name for frame in selected]
        self.assertEqual(frame_analysis.OPENAI_FRAME_ANALYSIS_MAX_FRAMES, 10)
        self.assertEqual(refs[0], "frame_001.jpg")
        self.assertEqual(refs[-1], "frame_012.jpg")
        self.assertIn("frame_006.jpg", refs)
        self.assertIn("frame_007.jpg", refs)
        self.assertEqual(metadata["available_frame_count"], 12)
        self.assertEqual(metadata["selected_frame_count"], 10)

    def test_openai_frame_selection_prioritizes_yolo_ranked_event_window(self):
        frame_analysis.OPENAI_FRAME_ANALYSIS_MAX_FRAMES = 6

        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 13):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({
                    "path": str(frame_path),
                    "time_sec": index * 0.5,
                    "role": "accident_candidate" if index in {9, 10} else "time_sequence",
                    "event_candidate_id": "event_window_2" if index in {8, 9, 10} else "event_window_1",
                    "vision_event_candidate_rank": 1 if index in {8, 9, 10} else 2,
                })

            selected = frame_analysis._select_openai_frames(frames, 6)

        refs = [Path(frame["path"]).name for frame in selected]
        self.assertIn("frame_001.jpg", refs)
        self.assertIn("frame_012.jpg", refs)
        self.assertTrue({"frame_008.jpg", "frame_009.jpg", "frame_010.jpg"} <= set(refs))

    def test_error_retry_frames_focus_on_event_summary_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 19):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({
                    "path": str(frame_path),
                    "time_sec": index * 0.5,
                    "role": "accident_candidate" if index in {10, 11, 12} else "time_sequence",
                    "event_phase": "event_candidate" if index in {10, 11, 12} else None,
                })

            retry_frames = frame_analysis._error_retry_frames(frames)

        refs = [Path(frame["path"]).name for frame in retry_frames]
        self.assertLessEqual(len(refs), 10)
        self.assertIn("frame_009.jpg", refs)
        self.assertIn("frame_010.jpg", refs)
        self.assertIn("frame_011.jpg", refs)

    def test_target_retry_frames_with_crops_adds_zoomed_road_regions(self):
        try:
            from PIL import Image
        except Exception:
            self.skipTest("Pillow is not available")
        frame_analysis.OPENAI_FRAME_ANALYSIS_TARGET_RETRY_CROPS = True
        frame_analysis.OPENAI_FRAME_ANALYSIS_TARGET_RETRY_ENHANCE = True
        frame_analysis.OPENAI_FRAME_ANALYSIS_TARGET_RETRY_MAX_CROPS = 3

        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 4):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                Image.new("RGB", (640, 360), "black").save(frame_path)
                frames.append({
                    "path": str(frame_path),
                    "time_sec": index,
                    "role": "accident_candidate" if index == 2 else "time_sequence",
                    "event_phase": "event_candidate" if index == 2 else None,
                })

            retry_frames = frame_analysis._target_retry_frames_with_crops(
                frames,
                {"event_frame_refs": ["frame_002.jpg"]},
            )

            crop_frames = [frame for frame in retry_frames if frame.get("role") == "target_retry_crop"]
            self.assertEqual(len(crop_frames), 3)
            self.assertTrue(all(Path(frame["path"]).exists() for frame in crop_frames))
            self.assertEqual({frame["parent_frame_ref"] for frame in crop_frames}, {"frame_002.jpg"})
            self.assertEqual(
                {frame["crop_region"] for frame in crop_frames},
                {"road_full", "road_center", "road_left"},
            )
            self.assertTrue(all(frame["path"].endswith("_enhanced.jpg") for frame in crop_frames))

    def test_target_retry_frames_keep_temporal_anchors_when_event_window_is_wrong(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 27):
                frame_path = Path(tmp) / f"frame_{index}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({
                    "path": str(frame_path),
                    "time_sec": index,
                    "role": "accident_candidate" if index in {13, 14} else "time_sequence",
                    "event_phase": "event_candidate" if index in {13, 14} else None,
                })

            retry_frames = frame_analysis._target_retry_frames(
                frames,
                {"event_frame_refs": ["frame_13.jpg", "frame_14.jpg"]},
            )

        refs = {Path(frame["path"]).name for frame in retry_frames}
        self.assertLessEqual(len(refs), 10)
        self.assertIn("frame_13.jpg", refs)
        self.assertIn("frame_14.jpg", refs)
        self.assertIn("frame_1.jpg", refs)
        self.assertIn("frame_26.jpg", refs)
        self.assertIn("frame_20.jpg", refs)

    def test_ambiguous_vehicle_only_target_runs_target_retry(self):
        calls = []

        def fake_post_json(url, payload, headers=None, timeout=25):
            calls.append(payload)
            if len(calls) == 1:
                return {
                    "id": "resp_primary",
                    "status": "completed",
                    "output_text": (
                        '{"observations":['
                        '{"field":"primary_collision_target","value":"vehicle_candidate","confidence":0.71,'
                        '"frame_refs":["frame_003.jpg","frame_004.jpg"],"reason":"traffic visible but target unclear"}]}'
                    ),
                }
            return {
                "id": "resp_target_retry",
                "status": "completed",
                "output_text": (
                    '{"observations":['
                    '{"field":"primary_collision_target","value":"bicycle_candidate","confidence":0.76,'
                    '"frame_refs":["frame_004.jpg","frame_005.jpg"],"reason":"small two-wheeled target visible near contact window"}]}'
                ),
            }

        frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS = True
        frame_analysis.FRAME_ANALYSIS_FIXTURE_MODE = ""
        frame_analysis.OPENAI_API_KEY = "test-key"
        frame_analysis.OPENAI_VISION_MODEL = "gpt-4.1-mini"
        frame_analysis.OPENAI_FRAME_ANALYSIS_RETRY_MODEL = "gpt-4.1"
        frame_analysis.OPENAI_FRAME_ANALYSIS_TARGET_RETRY = True
        frame_analysis.OPENAI_FRAME_ANALYSIS_AMBIGUOUS_TARGET_RETRY = True
        frame_analysis.OPENAI_FRAME_ANALYSIS_TARGET_RETRY_CROPS = False
        frame_analysis.OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES = 6
        frame_analysis._post_json = fake_post_json

        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 7):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({
                    "path": str(frame_path),
                    "time_sec": index,
                    "role": "accident_candidate" if index in {3, 4} else "time_sequence",
                    "event_phase": "event_candidate" if index in {3, 4} else None,
                })
            result = frame_analysis.analyze_frames_with_openai(frames, {})

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["model"], "gpt-4.1-mini")
        self.assertEqual(calls[1]["model"], "gpt-4.1")
        self.assertEqual([item["label"] for item in result["analysis_attempts"]], ["primary", "target_observation_retry"])
        self.assertEqual(result["analysis_attempts"][1]["model"], "gpt-4.1")
        targets = [(item["field"], item["value"]) for item in result["observations"]]
        self.assertIn(("primary_collision_target", "vehicle_candidate"), targets)
        self.assertIn(("primary_collision_target", "bicycle_candidate"), targets)

    def test_gpt5_payload_uses_cost_controls_without_temperature(self):
        captured = {}

        def fake_post_json(url, payload, headers=None, timeout=25):
            captured["url"] = url
            captured["payload"] = payload
            return {
                "id": "resp_123",
                "status": "completed",
                "usage": {"input_tokens": 120, "output_tokens": 45, "total_tokens": 165},
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
        self.assertEqual(result["ai_usage_event"]["version"], "ai-usage-event-v1")
        self.assertEqual(result["ai_usage_event"]["provider"], "openai")
        self.assertEqual(result["ai_usage_event"]["endpoint"], "responses")
        self.assertEqual(result["ai_usage_event"]["model"], "gpt-5-nano")
        self.assertEqual(result["ai_usage_event"]["selected_frame_count"], 1)
        self.assertEqual(result["ai_usage_event"]["usage"]["total_tokens"], 165)
        self.assertNotIn("api_key", json.dumps(result["ai_usage_event"]).lower())

    def test_non_gpt5_payload_uses_temperature_zero(self):
        self.assertEqual(frame_analysis._generation_controls_for_model("gpt-4.1-mini"), {"temperature": 0})
        self.assertNotIn("verbosity", frame_analysis._text_options_for_model("gpt-4.1-mini"))

    def test_zero_observation_retry_runs_once_when_frames_are_sufficient(self):
        calls = []

        def fake_post_json(url, payload, headers=None, timeout=25):
            calls.append(payload)
            if len(calls) == 1:
                return {
                    "id": "resp_primary",
                    "status": "completed",
                    "output_text": (
                        '{"accident_event_summary":{"impact_visible":false,'
                        '"pre_impact_frame_refs":["frame_001.jpg","frame_002.jpg"],'
                        '"post_impact_frame_refs":["frame_006.jpg"],'
                        '"rationale":"no visible contact in first pass"},'
                        '"observations":[]}'
                    ),
                }
            return {
                "id": "resp_retry",
                "status": "completed",
                "output_text": (
                    '{"accident_event_summary":{"impact_visible":true,'
                    '"event_frame_refs":["frame_004.jpg","frame_005.jpg"],'
                    '"pre_impact_frame_refs":["frame_003.jpg"],'
                    '"post_impact_frame_refs":["frame_006.jpg"],'
                    '"rationale":"retry found impact context"},'
                    '"observations":['
                    '{"field":"collision_partner_type","value":"vehicle","confidence":0.91,'
                    '"frame_refs":["frame_004.jpg","frame_005.jpg"],"reason":"vehicle contact is visible"}]}'
                ),
            }

        frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS = True
        frame_analysis.FRAME_ANALYSIS_FIXTURE_MODE = ""
        frame_analysis.OPENAI_API_KEY = "test-key"
        frame_analysis.OPENAI_VISION_MODEL = "gpt-4.1-mini"
        frame_analysis.OPENAI_FRAME_ANALYSIS_ZERO_OBSERVATION_RETRY = True
        frame_analysis.OPENAI_FRAME_ANALYSIS_TARGET_RETRY = False
        frame_analysis.OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES = 6
        frame_analysis._post_json = fake_post_json

        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 7):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({"path": str(frame_path), "time_sec": index, "role": "time_sequence"})
            result = frame_analysis.analyze_frames_with_openai(frames, {})

        self.assertEqual(len(calls), 2)
        retry_prompt = calls[1]["input"][0]["content"][0]["text"]
        self.assertIn("bounded retry", retry_prompt)
        self.assertTrue(result["zero_observation_retry_used"])
        self.assertEqual(result["response_id"], "resp_retry")
        self.assertEqual(result["observations"][0]["field"], "collision_partner_type")
        self.assertEqual(result["accident_event_summary"]["event_frame_refs"], ["frame_004.jpg", "frame_005.jpg"])
        self.assertEqual([item["label"] for item in result["analysis_attempts"]], ["primary", "zero_observation_retry"])

    def test_zero_observation_retry_is_skipped_for_short_frame_sets(self):
        calls = []

        def fake_post_json(url, payload, headers=None, timeout=25):
            calls.append(payload)
            return {"id": "resp_primary", "status": "completed", "output_text": '{"observations":[]}'}

        frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS = True
        frame_analysis.FRAME_ANALYSIS_FIXTURE_MODE = ""
        frame_analysis.OPENAI_API_KEY = "test-key"
        frame_analysis.OPENAI_VISION_MODEL = "gpt-4.1-mini"
        frame_analysis.OPENAI_FRAME_ANALYSIS_ZERO_OBSERVATION_RETRY = True
        frame_analysis.OPENAI_FRAME_ANALYSIS_TARGET_RETRY = False
        frame_analysis.OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES = 6
        frame_analysis._post_json = fake_post_json

        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 4):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({"path": str(frame_path), "time_sec": index, "role": "time_sequence"})
            result = frame_analysis.analyze_frames_with_openai(frames, {})

        self.assertEqual(len(calls), 1)
        self.assertFalse(result["zero_observation_retry_used"])
        self.assertEqual(result["observations"], [])

    def test_zero_observation_retry_falls_back_to_limited_visual_observation(self):
        calls = []

        def fake_post_json(url, payload, headers=None, timeout=25):
            calls.append(payload)
            return {
                "id": f"resp_{len(calls)}",
                "status": "completed",
                "output_text": (
                    '{"accident_event_summary":{"impact_visible":false,'
                    '"event_frame_refs":["frame_004.jpg"],'
                    '"rationale":"dark frames with no reliable physical fact"},'
                    '"observations":[]}'
                ),
            }

        frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS = True
        frame_analysis.FRAME_ANALYSIS_FIXTURE_MODE = ""
        frame_analysis.OPENAI_API_KEY = "test-key"
        frame_analysis.OPENAI_VISION_MODEL = "gpt-4.1-mini"
        frame_analysis.OPENAI_FRAME_ANALYSIS_ZERO_OBSERVATION_RETRY = True
        frame_analysis.OPENAI_FRAME_ANALYSIS_TARGET_RETRY = False
        frame_analysis.OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES = 6
        frame_analysis._post_json = fake_post_json

        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 7):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({"path": str(frame_path), "time_sec": index, "role": "time_sequence"})
            result = frame_analysis.analyze_frames_with_openai(frames, {})

        self.assertEqual(len(calls), 2)
        self.assertTrue(result["zero_observation_retry_used"])
        fields = [item["field"] for item in result["observations"]]
        self.assertEqual(fields, ["accident_event_candidate", "visual_evidence_limited"])
        self.assertEqual(result["observations"][0]["frame_refs"], ["frame_004.jpg"])
        self.assertEqual(result["observations"][1]["value"], True)
        self.assertEqual(result["observations"][1]["frame_refs"], ["frame_004.jpg"])
        self.assertEqual(result["observation_quality_summary"]["observation_count"], 2)

    def test_transient_openai_timeout_runs_bounded_error_retry(self):
        calls = []

        def fake_post_json(url, payload, headers=None, timeout=25):
            calls.append(payload)
            if len(calls) == 1:
                raise TimeoutError("The read operation timed out")
            return {
                "id": "resp_retry_after_timeout",
                "status": "completed",
                "output_text": (
                    '{"accident_event_summary":{"impact_visible":true,'
                    '"event_frame_refs":["frame_004.jpg","frame_005.jpg"],'
                    '"rationale":"retry found impact context"},'
                    '"observations":['
                    '{"field":"collision_partner_type","value":"vehicle","confidence":0.92,'
                    '"frame_refs":["frame_004.jpg","frame_005.jpg"],"reason":"vehicle contact is visible"}]}'
                ),
            }

        frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS = True
        frame_analysis.FRAME_ANALYSIS_FIXTURE_MODE = ""
        frame_analysis.OPENAI_API_KEY = "test-key"
        frame_analysis.OPENAI_VISION_MODEL = "gpt-4.1-mini"
        frame_analysis.OPENAI_FRAME_ANALYSIS_ERROR_RETRY = True
        frame_analysis.OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES = 6
        frame_analysis._post_json = fake_post_json

        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 7):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({"path": str(frame_path), "time_sec": index, "role": "time_sequence"})
            result = frame_analysis.analyze_frames_with_openai(frames, {})

        self.assertEqual(len(calls), 2)
        retry_prompt = calls[1]["input"][0]["content"][0]["text"]
        self.assertIn("bounded retry", retry_prompt)
        self.assertTrue(result["error_retry_used"])
        self.assertEqual(result["error_retry_error"], "")
        self.assertEqual(result["response_id"], "resp_retry_after_timeout")
        self.assertEqual(result["observations"][0]["field"], "collision_partner_type")
        self.assertEqual([item["label"] for item in result["analysis_attempts"]], ["primary", "error_retry"])
        self.assertEqual(result["analysis_attempts"][0]["response_status"], "error")

    def test_transient_openai_timeout_retry_can_fall_back_to_limited_visual_observation(self):
        calls = []

        def fake_post_json(url, payload, headers=None, timeout=25):
            calls.append(payload)
            if len(calls) == 1:
                raise TimeoutError("The read operation timed out")
            return {
                "id": "resp_retry_after_timeout",
                "status": "completed",
                "output_text": '{"observations":[]}',
            }

        frame_analysis.ENABLE_OPENAI_FRAME_ANALYSIS = True
        frame_analysis.FRAME_ANALYSIS_FIXTURE_MODE = ""
        frame_analysis.OPENAI_API_KEY = "test-key"
        frame_analysis.OPENAI_VISION_MODEL = "gpt-4.1-mini"
        frame_analysis.OPENAI_FRAME_ANALYSIS_ERROR_RETRY = True
        frame_analysis.OPENAI_FRAME_ANALYSIS_RETRY_MIN_FRAMES = 6
        frame_analysis._post_json = fake_post_json

        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 7):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({"path": str(frame_path), "time_sec": index, "role": "time_sequence"})
            result = frame_analysis.analyze_frames_with_openai(frames, {})

        self.assertEqual(len(calls), 3)
        self.assertTrue(result["error_retry_used"])
        self.assertEqual(result["observations"][0]["field"], "visual_evidence_limited")
        self.assertEqual([item["label"] for item in result["analysis_attempts"]], ["primary", "error_retry", "target_observation_retry"])
        self.assertEqual(result["analysis_attempts"][0]["response_status"], "error")

    def test_prompt_and_confidence_gate_reduce_negative_stopped_false_positives(self):
        captured = {}

        def fake_post_json(url, payload, headers=None, timeout=25):
            captured["payload"] = payload
            return {
                "id": "resp_stopped_false",
                "output_text": (
                    '{"accident_event_summary":{"impact_visible":true,'
                    '"event_frame_refs":["frame_002.jpg"],'
                    '"pre_impact_frame_refs":["frame_001.jpg"],'
                    '"post_impact_frame_refs":["frame_003.jpg"],'
                    '"rationale":"impact evidence appears after the initial frame"},'
                    '"observations":['
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
        frame_text = captured["payload"]["input"][0]["content"][1]["text"]
        self.assertIn("Use it only to prioritize which visual facts to inspect", prompt_text)
        self.assertIn("identify the accident target/object, collision point, and collision partner first", prompt_text)
        self.assertIn("inspect every provided frame_ref in chronological order", prompt_text)
        self.assertIn("event_candidate_id and event_phase metadata", prompt_text)
        self.assertIn("compare the pre_event_context, event_candidate, and post_event_context frames", prompt_text)
        self.assertIn("Do not treat the first risky scene", prompt_text)
        self.assertIn("multiple possible event candidates", prompt_text)
        self.assertIn("accident_event_summary", prompt_text)
        self.assertIn("Do not mark stopped=false merely because the dashcam image changes", prompt_text)
        self.assertIn("centerline_crossed", prompt_text)
        self.assertIn("collision_partner_type", prompt_text)
        self.assertIn("front_vehicle_stopped", prompt_text)
        self.assertIn("opponent_signal_visible=false", prompt_text)
        self.assertIn("highway_or_expressway", prompt_text)
        self.assertIn("pedestrian_visible", prompt_text)
        self.assertIn("never infer a pedestrian accident from crosswalk_nearby alone", prompt_text)
        self.assertIn("event_candidate_id=", frame_text)
        self.assertIn("event_phase=", frame_text)
        self.assertEqual(result["observations"][0]["field"], "stopped")
        self.assertEqual(result["observations"][0]["value"], False)
        self.assertEqual(result["observations"][0]["confidence"], 0.81)
        self.assertEqual(result["observations"][0]["observation_quality"]["level"], "low")
        self.assertEqual(result["accident_event_summary"]["event_frame_refs"], ["frame_002.jpg"])

    def test_openai_normalizer_keeps_road_context_and_target_absence_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            frame_path = Path(tmp) / "frame_001.jpg"
            frame_path.write_bytes(b"exists")
            selected_frames = [{"path": str(frame_path), "time_sec": 0.5, "role": "time_sequence"}]

            observations = frame_analysis._normalize_openai_observations(
                [
                    {
                        "field": "centerline_crossed",
                        "value": True,
                        "confidence": 0.91,
                        "frame_refs": ["frame_001.jpg"],
                        "reason": "yellow centerline crossed to pass a parked vehicle",
                    },
                    {
                        "field": "pedestrian_visible",
                        "value": False,
                        "confidence": 0.95,
                        "frame_refs": ["frame_001.jpg"],
                        "reason": "no pedestrian visible",
                    },
                ],
                selected_frames,
            )

        self.assertEqual(len(observations), 2)
        self.assertEqual(observations[0]["field"], "centerline_crossed")
        self.assertEqual(observations[0]["value"], True)
        self.assertEqual(observations[1]["field"], "pedestrian_visible")
        self.assertEqual(observations[1]["value"], False)

    def test_openai_normalizer_softens_ego_vehicle_partner_contradiction(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 4):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({"path": str(frame_path), "time_sec": index, "role": "time_sequence"})

            observations = frame_analysis._normalize_openai_observations(
                [
                    {
                        "field": "primary_collision_target",
                        "value": "pedestrian",
                        "confidence": 0.96,
                        "frame_refs": ["frame_001.jpg", "frame_002.jpg", "frame_003.jpg"],
                    },
                    {
                        "field": "collision_partner_type",
                        "value": "vehicle",
                        "confidence": 0.96,
                        "frame_refs": ["frame_001.jpg", "frame_002.jpg", "frame_003.jpg"],
                    },
                ],
                frames,
            )

        self.assertFalse([item for item in observations if item["field"] == "collision_partner_type"])
        partner = [item for item in observations if item["field"] == "primary_collision_target" and item["value"] == "vehicle_candidate"][0]
        self.assertEqual(partner["confidence"], 0.74)
        self.assertIn("ego_vehicle_partner_ambiguity", partner["reason"])

    def test_openai_normalizer_maps_post_impact_non_vehicle_to_target_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(12, 20):
                frame_path = Path(tmp) / f"frame_{index}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({"path": str(frame_path), "time_sec": index, "role": "time_sequence"})

            observations = frame_analysis._normalize_openai_observations(
                [
                    {
                        "field": "collision_partner_type",
                        "value": "vehicle",
                        "confidence": 0.95,
                        "frame_refs": ["frame_12.jpg", "frame_13.jpg", "frame_14.jpg", "frame_15.jpg"],
                    },
                    {
                        "field": "motorcycle_visible_post_impact",
                        "value": True,
                        "confidence": 0.9,
                        "frame_refs": ["frame_17.jpg", "frame_18.jpg", "frame_19.jpg"],
                    },
                ],
                frames,
            )

        self.assertFalse([item for item in observations if item["field"] == "collision_partner_type"])
        targets = [item for item in observations if item["field"] == "primary_collision_target"]
        self.assertEqual([item["value"] for item in targets], ["vehicle_candidate", "motorcycle_candidate"])
        self.assertLess(targets[0]["confidence"], 0.75)
        self.assertIn("ego_vehicle_partner_ambiguity", targets[0]["reason"])
        self.assertIn("post_impact_non_vehicle_target_candidate", targets[1]["reason"])

    def test_openai_normalizer_softens_single_frame_non_vehicle_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            frame_path = Path(tmp) / "frame_001.jpg"
            frame_path.write_bytes(b"exists")
            selected_frames = [{"path": str(frame_path), "time_sec": 0.5, "role": "time_sequence"}]

            observations = frame_analysis._normalize_openai_observations(
                [
                    {
                        "field": "direct_collision_partner_type",
                        "value": "bicycle",
                        "confidence": 0.95,
                        "frame_refs": ["frame_001.jpg"],
                    },
                    {
                        "field": "primary_collision_target",
                        "value": "bicycle",
                        "confidence": 0.95,
                        "frame_refs": ["frame_001.jpg"],
                    },
                ],
                selected_frames,
            )

        by_field = {item["field"]: item for item in observations}
        self.assertEqual(by_field["direct_collision_partner_type"]["confidence"], 0.74)
        self.assertEqual(by_field["primary_collision_target"]["confidence"], 0.74)

    def test_event_summary_can_be_derived_from_collision_observations(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 7):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({"path": str(frame_path), "time_sec": index, "role": "time_sequence"})
            summary = frame_analysis._derive_accident_event_summary_from_observations(
                [
                    {
                        "field": "collision_partner_type",
                        "value": "vehicle",
                        "confidence": 0.91,
                        "frame_refs": ["frame_003.jpg", "frame_004.jpg"],
                    },
                    {
                        "field": "pedestrian_visible",
                        "value": False,
                        "confidence": 0.95,
                        "frame_refs": ["frame_001.jpg", "frame_002.jpg"],
                    },
                ],
                frames,
            )

        self.assertTrue(summary["impact_visible"])
        self.assertEqual(summary["event_frame_refs"], ["frame_003.jpg", "frame_004.jpg"])
        self.assertEqual(summary["pre_impact_frame_refs"], ["frame_001.jpg", "frame_002.jpg"])
        self.assertEqual(summary["post_impact_frame_refs"], ["frame_005.jpg", "frame_006.jpg"])

    def test_openai_selection_prioritizes_accident_candidate_frames(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 19):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({
                    "path": str(frame_path),
                    "time_sec": index,
                    "role": "accident_candidate" if index in {11, 12} else "time_sequence",
                })

            selected = frame_analysis._select_openai_frames(frames, 8)

        refs = [Path(frame["path"]).name for frame in selected]
        self.assertIn("frame_011.jpg", refs)
        self.assertIn("frame_012.jpg", refs)
        self.assertIn("frame_001.jpg", refs)
        self.assertIn("frame_018.jpg", refs)

    def test_openai_selection_spreads_multiple_event_candidates_across_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 31):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({
                    "path": str(frame_path),
                    "time_sec": index,
                    "role": "accident_candidate" if index in {3, 4, 12, 13, 26, 27} else "time_sequence",
                })

            selected = frame_analysis._select_openai_frames(frames, 8)

        refs = [Path(frame["path"]).name for frame in selected]
        self.assertIn("frame_001.jpg", refs)
        self.assertIn("frame_030.jpg", refs)
        self.assertTrue({"frame_003.jpg", "frame_004.jpg"} & set(refs))
        self.assertTrue({"frame_012.jpg", "frame_013.jpg"} & set(refs))
        self.assertTrue({"frame_026.jpg", "frame_027.jpg"} & set(refs))


if __name__ == "__main__":
    unittest.main()
