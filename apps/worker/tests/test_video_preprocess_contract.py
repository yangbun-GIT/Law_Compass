import unittest

from worker.video_preprocess import event_focused_frame_times, frame_times_for_duration, summarize_frame_selection


class VideoPreprocessContractTest(unittest.TestCase):
    def test_short_accident_video_gets_dense_representative_frames(self):
        times = frame_times_for_duration(5.0)

        self.assertGreaterEqual(len(times), 14)
        self.assertLessEqual(len(times), 18)
        self.assertEqual(times[0], 0.0)
        self.assertAlmostEqual(times[-1], 4.9, places=1)

    def test_ten_second_accident_video_keeps_more_context_than_openai_budget(self):
        times = frame_times_for_duration(10.0)

        self.assertEqual(len(times), 18)
        self.assertIn(0.2, times)
        self.assertLessEqual(min(abs(value - 5.0) for value in times), 0.3)
        self.assertAlmostEqual(times[-1], 9.9, places=1)

    def test_longer_video_is_capped_for_storage_and_cost_control(self):
        times = frame_times_for_duration(45.0)

        self.assertEqual(len(times), 18)
        self.assertEqual(times[0], 0.0)
        self.assertAlmostEqual(times[-1], 44.9, places=1)

    def test_long_video_with_event_signal_prioritizes_accident_window(self):
        times = frame_times_for_duration(120.0, event_times=[72.4])

        self.assertLessEqual(len(times), 18)
        self.assertEqual(times[0], 0.0)
        self.assertAlmostEqual(times[-1], 119.9, places=1)
        self.assertTrue(any(abs(value - 72.4) <= 0.5 for value in times))
        self.assertGreaterEqual(sum(1 for value in times if abs(value - 72.4) <= 4), 6)

    def test_frame_selection_summary_counts_accident_candidates(self):
        summary = summarize_frame_selection([
            {"role": "start_context", "selection_reason": "representative_time_context"},
            {"role": "accident_candidate", "selection_reason": "near_scene_change_accident_candidate"},
            {"role": "event_context", "selection_reason": "near_scene_change_context"},
        ])

        self.assertEqual(summary["strategy"], "scene-change-prioritized-object-first-frame-selection")
        self.assertEqual(summary["accident_candidate_count"], 1)
        self.assertEqual(summary["event_context_count"], 1)


if __name__ == "__main__":
    unittest.main()
