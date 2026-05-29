import tempfile
import unittest
from pathlib import Path

from worker import yolo_frame_analysis


class _Scalar:
    def __init__(self, value):
        self.value = value

    def item(self):
        return self.value


class _Vector:
    def __init__(self, values):
        self.values = values

    def tolist(self):
        return self.values


class _FakeBox:
    def __init__(self, class_id, confidence, xyxy=None):
        self.cls = [_Scalar(class_id)]
        self.conf = [_Scalar(confidence)]
        self.xyxy = [_Vector(xyxy or [1, 2, 3, 4])]


class _FakeResult:
    def __init__(self, path, names, boxes, orig_shape=(720, 1280)):
        self.path = path
        self.names = names
        self.boxes = boxes
        self.orig_shape = orig_shape


class YoloFrameAnalysisContractTest(unittest.TestCase):
    def setUp(self):
        self._enabled = yolo_frame_analysis.ENABLE_YOLO_FRAME_ANALYSIS
        self._model_path = yolo_frame_analysis.YOLO_MODEL_PATH
        self._max_frames = yolo_frame_analysis.YOLO_FRAME_ANALYSIS_MAX_FRAMES
        self._max_frame_refs = yolo_frame_analysis.YOLO_MAX_FRAME_REFS

    def tearDown(self):
        yolo_frame_analysis.ENABLE_YOLO_FRAME_ANALYSIS = self._enabled
        yolo_frame_analysis.YOLO_MODEL_PATH = self._model_path
        yolo_frame_analysis.YOLO_FRAME_ANALYSIS_MAX_FRAMES = self._max_frames
        yolo_frame_analysis.YOLO_MAX_FRAME_REFS = self._max_frame_refs

    def test_disabled_mode_reports_available_frames_without_model_loading(self):
        yolo_frame_analysis.ENABLE_YOLO_FRAME_ANALYSIS = False

        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 4):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({"path": str(frame_path), "time_sec": index, "role": "time_sequence"})
            result = yolo_frame_analysis.analyze_frames_with_yolo(frames, {"upload_id": "upload-1"})

        self.assertFalse(result["enabled"])
        self.assertEqual(result["reason"], "ENABLE_YOLO_FRAME_ANALYSIS is not 1")
        self.assertEqual(result["available_frame_count"], 3)
        self.assertEqual(result["selected_frame_count"], 3)
        self.assertEqual(result["frame_selection_strategy"], yolo_frame_analysis.YOLO_FRAME_SELECTION_STRATEGY)

    def test_enabled_without_model_path_returns_configuration_reason(self):
        yolo_frame_analysis.ENABLE_YOLO_FRAME_ANALYSIS = True
        yolo_frame_analysis.YOLO_MODEL_PATH = ""

        with tempfile.TemporaryDirectory() as tmp:
            frame_path = Path(tmp) / "frame_001.jpg"
            frame_path.write_bytes(b"exists")
            result = yolo_frame_analysis.analyze_frames_with_yolo(
                [{"path": str(frame_path), "time_sec": 0.5, "role": "time_sequence"}],
                {},
            )

        self.assertFalse(result["enabled"])
        self.assertEqual(result["reason"], "YOLO_MODEL_PATH is empty")

    def test_yolo_candidates_are_capped_below_agent_fact_threshold(self):
        observations = yolo_frame_analysis._observation_candidates(
            {
                "person": {"frame_001.jpg", "frame_002.jpg"},
                "car": {"frame_002.jpg", "frame_003.jpg"},
                "traffic light": {"frame_003.jpg"},
            },
            {
                "person": [0.98],
                "car": [0.99],
                "traffic light": [0.96],
            },
            max_frame_refs=4,
        )

        by_field = {item["field"]: item for item in observations}
        self.assertEqual(by_field["pedestrian_visible"]["source"], "vision_model:yolo")
        self.assertEqual(by_field["pedestrian_visible"]["confidence"], 0.74)
        self.assertEqual(by_field["opponent_signal_visible"]["confidence"], 0.74)
        self.assertEqual(by_field["primary_collision_target"]["value"], "vehicle_candidate")
        self.assertEqual(by_field["primary_collision_target"]["confidence"], 0.72)

    def test_yolo_payload_maps_results_by_selected_frame_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            frame_path = Path(tmp) / "source_frame_001.jpg"
            frame_path.write_bytes(b"exists")
            selected_frames = [{"path": str(frame_path), "time_sec": 0.5, "role": "time_sequence"}]

            payload = yolo_frame_analysis._build_yolo_payload(
                [_FakeResult("garbled_frame_name.jpg", {2: "car"}, [_FakeBox(2, 0.99)])],
                selected_frames,
                {"case_id": "case-1", "upload_id": "upload-1"},
                {"available_frame_count": 1, "selected_frame_count": 1, "frame_selection_strategy": "test"},
            )

        self.assertEqual(payload["summary"]["total_detections"], 1)
        self.assertEqual(payload["detections"][0]["frame_ref"], "source_frame_001.jpg")
        self.assertEqual(payload["observations"][0]["frame_refs"], ["source_frame_001.jpg"])

    def test_yolo_event_candidate_summary_ranks_vehicle_dense_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index, candidate_id in [(1, "event_window_1"), (2, "event_window_2"), (3, "event_window_2")]:
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({
                    "path": str(frame_path),
                    "time_sec": index,
                    "role": "accident_candidate",
                    "event_candidate_id": candidate_id,
                    "event_phase": "event_candidate",
                })

            payload = yolo_frame_analysis._build_yolo_payload(
                [
                    _FakeResult("ignored_1.jpg", {2: "car"}, [_FakeBox(2, 0.55, [1, 1, 50, 50])]),
                    _FakeResult("ignored_2.jpg", {2: "car"}, [_FakeBox(2, 0.92, [1, 1, 500, 400])]),
                    _FakeResult("ignored_3.jpg", {2: "car"}, [_FakeBox(2, 0.90, [1, 1, 480, 390])]),
                ],
                frames,
                {"case_id": "case-1", "upload_id": "upload-1"},
                {"available_frame_count": 3, "selected_frame_count": 3, "frame_selection_strategy": "test"},
            )

        summaries = payload["event_candidate_summary"]
        self.assertEqual(summaries[0]["event_candidate_id"], "event_window_2")
        self.assertEqual(payload["summary"]["top_event_candidate_id"], "event_window_2")

    def test_static_edge_person_overlay_is_ignored_before_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            results = []
            for index in range(1, 4):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({
                    "path": str(frame_path),
                    "time_sec": index,
                    "role": "event_candidate",
                    "event_candidate_id": "event_window_1",
                    "event_phase": "event_candidate",
                })
                results.append(
                    _FakeResult(
                        f"ignored_{index}.jpg",
                        {0: "person", 2: "car"},
                        [
                            _FakeBox(0, 0.97, [30, 30, 130, 180]),
                            _FakeBox(2, 0.95, [300, 260, 900, 650]),
                        ],
                    ),
                )

            payload = yolo_frame_analysis._build_yolo_payload(
                results,
                frames,
                {"case_id": "case-1", "upload_id": "upload-1"},
                {"available_frame_count": 3, "selected_frame_count": 3, "frame_selection_strategy": "test"},
            )

        by_field = {item["field"]: item for item in payload["observations"]}
        self.assertEqual(payload["summary"]["raw_detection_count"], 6)
        self.assertEqual(payload["summary"]["total_detections"], 3)
        self.assertEqual(payload["summary"]["ignored_detection_count"], 3)
        self.assertEqual(payload["summary"]["ignored_class_counts"], {"person": 3})
        self.assertEqual(payload["summary"]["class_counts"], {"car": 3})
        self.assertNotIn("pedestrian_visible", by_field)
        self.assertEqual(by_field["primary_collision_target"]["value"], "vehicle_candidate")
        self.assertEqual(payload["ignored_detections"][0]["ignore_reason"], "static_edge_overlay_or_broadcast_ui")

    def test_center_road_person_is_kept_as_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            results = []
            for index in range(1, 4):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({
                    "path": str(frame_path),
                    "time_sec": index,
                    "role": "event_candidate",
                    "event_candidate_id": "event_window_1",
                    "event_phase": "event_candidate",
                })
                results.append(
                    _FakeResult(
                        f"ignored_{index}.jpg",
                        {0: "person"},
                        [_FakeBox(0, 0.96, [520, 260, 620, 600])],
                    ),
                )

            payload = yolo_frame_analysis._build_yolo_payload(
                results,
                frames,
                {"case_id": "case-1", "upload_id": "upload-1"},
                {"available_frame_count": 3, "selected_frame_count": 3, "frame_selection_strategy": "test"},
            )

        by_field = {item["field"]: item for item in payload["observations"]}
        self.assertEqual(payload["summary"]["raw_detection_count"], 3)
        self.assertEqual(payload["summary"]["ignored_detection_count"], 0)
        self.assertEqual(payload["summary"]["class_counts"], {"person": 3})
        self.assertEqual(payload["ignored_detections"], [])
        self.assertEqual(by_field["pedestrian_visible"]["value"], True)

    def test_rank_frame_details_by_yolo_marks_top_candidate_for_openai_selection(self):
        frames = [
            {"path": "frame_001.jpg", "event_candidate_id": "event_window_1", "selection_reason": "event_window_context"},
            {"path": "frame_002.jpg", "event_candidate_id": "event_window_2", "selection_reason": "event_window_accident_candidate"},
        ]
        payload = {
            "enabled": True,
            "event_candidate_summary": [
                {"event_candidate_id": "event_window_2", "score": 8.5},
                {"event_candidate_id": "event_window_1", "score": 2.0},
            ],
        }

        result = yolo_frame_analysis.rank_frame_details_by_yolo(frames, payload)

        self.assertEqual(result[0]["vision_event_candidate_rank"], 2)
        self.assertEqual(result[1]["vision_event_candidate_rank"], 1)
        self.assertIn("yolo_ranked_event_candidate", result[1]["selection_reason"])

    def test_yolo_frame_selection_keeps_event_candidate_context(self):
        yolo_frame_analysis.YOLO_FRAME_ANALYSIS_MAX_FRAMES = 5

        with tempfile.TemporaryDirectory() as tmp:
            frames = []
            for index in range(1, 11):
                frame_path = Path(tmp) / f"frame_{index:03d}.jpg"
                frame_path.write_bytes(b"exists")
                frames.append({
                    "path": str(frame_path),
                    "time_sec": index,
                    "role": "accident_candidate" if index in {6, 7} else "time_sequence",
                })

            selected = yolo_frame_analysis._select_yolo_frames(
                frames,
                yolo_frame_analysis.YOLO_FRAME_ANALYSIS_MAX_FRAMES,
            )

        refs = [Path(frame["path"]).name for frame in selected]
        self.assertIn("frame_001.jpg", refs)
        self.assertTrue({"frame_006.jpg", "frame_007.jpg"} & set(refs))
        self.assertIn("frame_010.jpg", refs)


if __name__ == "__main__":
    unittest.main()
