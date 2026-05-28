import unittest

from worker.storage.base import frame_key, normalize_storage_key
from worker.storage.factory import create_storage_adapter


class WorkerStorageAdapterContractTest(unittest.TestCase):
    def test_normalize_storage_key_blocks_traversal(self):
        with self.assertRaises(ValueError):
            normalize_storage_key("../secret.mp4")
        with self.assertRaises(ValueError):
            normalize_storage_key("uploads/original/case/../../secret.mp4")
        self.assertEqual(
            normalize_storage_key(r"uploads\original\case\upload\original.mp4"),
            "uploads/original/case/upload/original.mp4",
        )

    def test_factory_selects_local_by_default(self):
        adapter = create_storage_adapter("local")
        self.assertEqual(adapter.driver, "local")

    def test_frame_key_uses_processed_frames_prefix(self):
        self.assertEqual(
            frame_key("case-1", "upload-1", "frame_1.jpg"),
            "processed/frames/case-1/upload-1/frame_1.jpg",
        )


if __name__ == "__main__":
    unittest.main()

