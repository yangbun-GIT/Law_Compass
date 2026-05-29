# Mobile ML Kit Video-Only Test Plan

## Purpose

This plan validates whether the app-packaging demo can extract on-device object candidates from a video and safely pass them toward server-side analysis as `client_pre_observations`.

The goal is not to determine legal responsibility on device. ML Kit output is an observation candidate only. Accident type, signal violation, KNIA chart, and fault ratio remain server Agent responsibilities.

## Test Account

Use an existing local admin or superuser account. Do not put the email, password, token, or seed secret in this document, source code, tests, commit messages, or screenshots.

Recommended local-only options:

- Keep credentials in `.env.local` or `.env.test.local`, which are ignored by Git.
- Type credentials manually in the normal login screen.
- If a local seed script is used, document only the command and placeholders, not the real password.

## Test Route

Enable the demo route in a local env file:

```env
VITE_ENABLE_APP_DEMO=true
VITE_APP_DEMO_ROUTE=/app-demo/mlkit
VITE_MLKIT_DEMO_MODE=true
```

Open `/app-demo/mlkit` after logging in. The video-only analysis button is available only to `admin` or `superuser` users. The Gateway enforces the same role check.

## Test Videos

Use short clips first, then increase duration and resolution.

| Scenario | Expected object candidates | Expected server result |
| --- | --- | --- |
| Rear-end collision | Vehicle candidates, possible multiple tracks | Possible `car_vs_car` major candidate; fault ratio usually `needs_review` without impact point and roles |
| Intersection side collision | Vehicle candidates, possible traffic light candidate | Possible `car_vs_car` and signal-related candidate; no signal violation confirmation |
| Lane-change contact | Vehicle candidates with lateral movement | Possible `car_vs_car`; lane relation remains missing unless server video analysis confirms |
| Pedestrian near-miss or contact | Person candidate, vehicle candidate if visible | Possible `car_vs_person`; no KNIA chart confirmation from ML Kit alone |
| Night parked vehicle collision | Vehicle candidate, possibly stationary track | Possible `car_vs_car`; parked/unlit status remains missing unless clearly confirmed elsewhere |

## Expected Missing Facts

Video-only ML Kit object detection should normally return missing facts such as:

- Collision moment
- Ego vehicle and opponent vehicle roles
- Signal state and signal transition
- Lane relationship
- Road shape
- Crosswalk, stop line, or parking status

If those facts are missing, success means the system returns `needs_review`, `reference_only`, and `missing_facts` instead of inventing a fault ratio.

## Success Criteria

- `/app-demo/mlkit` opens without changing the production analysis flow.
- Browser mode clearly shows native plugin unavailable or mock fallback.
- Android WebView attempts the native `MlKitObjectDetector` plugin.
- Exported JSON contains `client_pre_observations` with `object_candidate` values.
- Exported JSON does not contain `fault_ratio`, `accident_party_type`, `collision_partner_type`, `signal_violation`, `knia_chart_no`, or `legal_judgment`.
- `POST /api/v1/mobile-demo/video-only-analysis` returns `needs_review` when chart/fault facts are insufficient.
- General users receive 403 for video-only demo analysis.

## Failure Criteria

- ML Kit output directly sets fault ratio, signal violation, accident type, or KNIA chart.
- The demo calls an operational accident analysis endpoint behind the user's back.
- A real test password, API key, NAS credential, token, or local private path is committed.
- Empty or low-confidence observations crash the Gateway or Agent.

## Device Performance Log

| Device | Video length | Resolution | Sampling FPS | Processed frames | Avg processing ms | Detected objects | Tracked objects | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Galaxy ... | 10s | 1920x1080 | 2 | 20 | 0 | 0 | 0 |  |

