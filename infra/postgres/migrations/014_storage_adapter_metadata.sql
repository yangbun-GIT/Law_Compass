ALTER TABLE uploads
  ADD COLUMN IF NOT EXISTS storage_driver TEXT,
  ADD COLUMN IF NOT EXISTS storage_key TEXT,
  ADD COLUMN IF NOT EXISTS storage_path TEXT,
  ADD COLUMN IF NOT EXISTS original_filename TEXT,
  ADD COLUMN IF NOT EXISTS mime_type TEXT,
  ADD COLUMN IF NOT EXISTS size_bytes BIGINT,
  ADD COLUMN IF NOT EXISTS sha256 TEXT,
  ADD COLUMN IF NOT EXISTS storage_status TEXT,
  ADD COLUMN IF NOT EXISTS processed_frames_key TEXT,
  ADD COLUMN IF NOT EXISTS processed_clips_key TEXT,
  ADD COLUMN IF NOT EXISTS frame_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS clip_metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE uploads
SET storage_driver = COALESCE(storage_driver, storage_provider),
    storage_key = COALESCE(storage_key, s3_key),
    original_filename = COALESCE(original_filename, file_name),
    mime_type = COALESCE(mime_type, content_type),
    size_bytes = COALESCE(size_bytes, file_size_bytes),
    storage_status = COALESCE(storage_status, status::text)
WHERE storage_driver IS NULL
   OR storage_key IS NULL
   OR original_filename IS NULL
   OR mime_type IS NULL
   OR size_bytes IS NULL
   OR storage_status IS NULL;

CREATE INDEX IF NOT EXISTS idx_uploads_storage_driver_status ON uploads(storage_driver, storage_status);
CREATE INDEX IF NOT EXISTS idx_uploads_storage_key ON uploads(storage_key);
