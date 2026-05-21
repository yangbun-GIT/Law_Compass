def test_stream_key_naming():
    job_id = "abc"
    key = f"job:v1:{job_id}:status"
    assert key.startswith("job:v1:")

