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
    def __init__(self, class_id, confidence):
        self.cls = [_Scalar(class_id)]
        self.conf = [_Scalar(confidence)]
        self.xyxy = [_Vector([1, 2, 3, 4])]


class _FakeResult:
    def __init__(self, path, names, boxes):
        self.path = path
        self.names = names
        self.boxes = boxes


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
