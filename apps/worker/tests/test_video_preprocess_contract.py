import unittest

from worker.video_preprocess import frame_times_for_duration


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


if __name__ == "__main__":
    unittest.main()
