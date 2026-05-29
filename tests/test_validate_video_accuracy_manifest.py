import json
from pathlib import Path

from scripts.validate_video_accuracy_manifest import validate_manifest


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def error_codes(result: dict) -> set[str]:
    return {
        str(issue.get("code"))
        for issue in result.get("issues", [])
        if issue.get("severity") == "error"
    }


def test_manifest_rejects_reference_label_as_case_json(tmp_path: Path) -> None:
    label_path = tmp_path / "labels" / "sample_label.json"
    write_json(
        label_path,
        {
            "description_text": "차대차 사고 설명",
            "video": {"accident_object": 0, "traffic_accident_type": "car_to_car"},
        },
    )
    manifest_path = tmp_path / "manifest.json"
    write_json(
        manifest_path,
        {
            "samples": [
                {
                    "name": "bad_reference_leak",
                    "video_path": str(tmp_path / "video.mp4"),
                    "case_json": str(label_path),
                    "reference": {
                        "purpose": "evaluation_only_not_agent_input",
                        "label_json": str(label_path),
                    },
                }
            ]
        },
    )

    result = validate_manifest(
        manifest_path=manifest_path,
        min_samples=1,
        require_reference=True,
        allow_missing_files=True,
    )

    codes = error_codes(result)
    assert "reference_label_used_as_case_json" in codes
    assert "reference_token_in_case_json" in codes


def test_manifest_allows_separate_case_and_reference_label(tmp_path: Path) -> None:
    case_path = tmp_path / "cases" / "sample_case.json"
    label_path = tmp_path / "labels" / "sample_label.json"
    write_json(case_path, {"description_text": "교차로에서 좌회전 중 직진 차량과 충돌"})
    write_json(label_path, {"video": {"accident_object": 0, "traffic_accident_type": "car_to_car"}})
    manifest_path = tmp_path / "manifest.json"
    write_json(
        manifest_path,
        {
            "samples": [
                {
                    "name": "safe_reference",
                    "video_path": str(tmp_path / "video.mp4"),
                    "case_json": str(case_path),
                    "reference": {
                        "purpose": "evaluation_only_not_agent_input",
                        "label_json": str(label_path),
                    },
                }
            ]
        },
    )

    result = validate_manifest(
        manifest_path=manifest_path,
        min_samples=1,
        require_reference=True,
        allow_missing_files=True,
    )

    assert error_codes(result) == set()
