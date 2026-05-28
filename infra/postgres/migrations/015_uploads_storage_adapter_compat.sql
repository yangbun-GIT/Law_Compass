ALTER TABLE uploads ADD COLUMN IF NOT EXISTS storage_driver text;
ALTER TABLE uploads ADD COLUMN IF NOT EXISTS storage_key text;
ALTER TABLE uploads ADD COLUMN IF NOT EXISTS size_bytes bigint;
ALTER TABLE uploads ADD COLUMN IF NOT EXISTS sha256 text;
ALTER TABLE uploads ADD COLUMN IF NOT EXISTS original_filename text;
ALTER TABLE uploads ADD COLUMN IF NOT EXISTS mime_type text;
ALTER TABLE uploads ADD COLUMN IF NOT EXISTS storage_status text;

UPDATE uploads
SET storage_driver = COALESCE(storage_driver, storage_provider),
    storage_key = COALESCE(storage_key, s3_key),
    size_bytes = COALESCE(size_bytes, file_size_bytes),
    original_filename = COALESCE(original_filename, file_name),
    mime_type = COALESCE(mime_type, content_type),
    storage_status = COALESCE(storage_status, status::text)
WHERE storage_driver IS NULL
   OR storage_key IS NULL
   OR size_bytes IS NULL
   OR original_filename IS NULL
   OR mime_type IS NULL
   OR storage_status IS NULL;

CREATE INDEX IF NOT EXISTS idx_uploads_storage_driver_status ON uploads(storage_driver, storage_status);
CREATE INDEX IF NOT EXISTS idx_uploads_storage_key ON uploads(storage_key);
