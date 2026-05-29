import unittest

from worker.video_preprocess import (
    VIDEO_PREPROCESS_MAX_FRAMES,
    event_focused_frame_times,
    event_window_candidates,
    frame_times_for_duration,
    summarize_frame_selection,
    temporal_scan_windows,
    _event_frame_metadata,
    _event_phase,
    _frame_role,
    _selection_reason,
)


class VideoPreprocessContractTest(unittest.TestCase):
    def test_short_accident_video_gets_dense_representative_frames(self):
        times = frame_times_for_duration(5.0)

        self.assertGreaterEqual(len(times), 20)
        self.assertLessEqual(len(times), VIDEO_PREPROCESS_MAX_FRAMES)
        self.assertEqual(times[0], 0.0)
        self.assertAlmostEqual(times[-1], 4.9, places=1)

    def test_ten_second_accident_video_keeps_more_context_than_openai_budget(self):
        times = frame_times_for_duration(10.0)

        self.assertGreaterEqual(len(times), 24)
        self.assertLessEqual(len(times), VIDEO_PREPROCESS_MAX_FRAMES)
        self.assertIn(0.2, times)
        self.assertLessEqual(min(abs(value - 5.0) for value in times), 0.3)
        self.assertAlmostEqual(times[-1], 9.9, places=1)

    def test_longer_video_is_capped_for_storage_and_cost_control(self):
        times = frame_times_for_duration(45.0)

        self.assertEqual(len(times), VIDEO_PREPROCESS_MAX_FRAMES)
        self.assertEqual(times[0], 0.0)
        self.assertAlmostEqual(times[-1], 44.9, places=1)

    def test_long_video_with_event_signal_prioritizes_accident_window(self):
        times = frame_times_for_duration(120.0, event_times=[72.4])

        self.assertLessEqual(len(times), VIDEO_PREPROCESS_MAX_FRAMES)
        self.assertEqual(times[0], 0.0)
        self.assertAlmostEqual(times[-1], 119.9, places=1)
        self.assertTrue(any(abs(value - 72.4) <= 0.5 for value in times))
        self.assertGreaterEqual(sum(1 for value in times if abs(value - 72.4) <= 4), 6)

    def test_frame_selection_summary_counts_accident_candidates(self):
        summary = summarize_frame_selection([
            {"role": "start_context", "selection_reason": "representative_time_context"},
            {
                "role": "accident_candidate",
                "selection_reason": "event_window_accident_candidate",
                "event_candidate_id": "event_window_1",
                "event_phase": "event_candidate",
            },
            {
                "role": "event_context",
                "selection_reason": "event_window_context",
                "event_candidate_id": "event_window_1",
                "event_phase": "post_event_context",
            },
        ])

        self.assertEqual(summary["strategy"], "scene-change-windowed-event-frame-selection")
        self.assertEqual(summary["accident_candidate_count"], 1)
        self.assertEqual(summary["event_context_count"], 1)
        self.assertEqual(summary["event_window_candidate_count"], 1)
        self.assertFalse(summary["has_multiple_event_windows"])
        self.assertEqual(summary["event_phase_counts"]["event_candidate"], 1)

    def test_event_window_candidates_cluster_nearby_scene_changes(self):
        windows = event_window_candidates(30.0, [2.0, 2.6, 14.0, 14.8, 25.0])

        self.assertEqual([item["candidate_id"] for item in windows], ["event_window_1", "event_window_2", "event_window_3"])
        self.assertEqual(windows[0]["scene_change_count"], 2)
        self.assertAlmostEqual(windows[0]["center_time_sec"], 2.3, places=1)
        self.assertEqual(windows[1]["scene_change_count"], 2)

    def test_event_window_candidates_fall_back_to_temporal_scan_when_scene_detection_is_empty(self):
        windows = event_window_candidates(45.0, [])

        self.assertEqual([item["candidate_id"] for item in windows], ["temporal_window_1", "temporal_window_2", "temporal_window_3"])
        self.assertTrue(all(item["source"] == "temporal_scan_fallback" for item in windows))
        self.assertEqual([item["scene_change_count"] for item in windows], [0, 0, 0])

    def test_temporal_scan_windows_keep_short_video_single_middle_candidate(self):
        windows = temporal_scan_windows(6.0)

        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0]["candidate_id"], "temporal_window_1")
        self.assertAlmostEqual(windows[0]["center_time_sec"], 3.0, places=1)

    def test_event_window_phase_marks_pre_event_and_post_event_context(self):
        windows = event_window_candidates(20.0, [10.0])

        pre = _event_phase(7.0, windows)
        event = _event_phase(10.0, windows)
        post = _event_phase(13.5, windows)

        self.assertEqual(pre["phase"], "pre_event_context")
        self.assertEqual(event["phase"], "event_candidate")
        self.assertEqual(post["phase"], "post_event_context")
        self.assertEqual(_frame_role(2, 10, event), "accident_candidate")
        self.assertEqual(_selection_reason(event), "event_window_accident_candidate")
        self.assertEqual(_event_frame_metadata(event)["event_candidate_id"], "event_window_1")


if __name__ == "__main__":
    unittest.main()
