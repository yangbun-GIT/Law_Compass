# Reference Hardening Minimal Fixture

This fixture verifies the reference-guidance evaluation chain without local `logs/` inputs or real accident videos.

It is synthetic and intentionally excludes:
- real video paths
- real user data
- API keys or secrets
- real lawyer opinion text

Expected checks:
- `reference_guidance_eval.py`: 1 ready sample and 1 conflict-gated sample
- `reference_evidence_alignment_eval.py`: 1 ready evidence-alignment sample
- `reference_guidance_calibration_eval.py`: 1 calibrated sample and 1 `blocked_by_reference_gate` sample
