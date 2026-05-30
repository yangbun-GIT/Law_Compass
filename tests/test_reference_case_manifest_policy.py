import json
from pathlib import Path

from scripts.aihub597_labels_to_manifest import build_case
from scripts.validate_reference_case_manifest import validate_manifest


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def error_codes(result: dict) -> set[str]:
    return {
        str(issue.get("code"))
        for issue in result.get("issues", [])
        if issue.get("severity") == "error"
    }


def test_reference_manifest_rejects_embedded_agent_input_payload(tmp_path: Path) -> None:
    manifest_path = tmp_path / "reference_manifest.json"
    write_json(
        manifest_path,
        {
            "version": "test",
            "cases": [
                {
                    "id": "bad_agent_payload",
                    "source_type": "aihub_sample",
                    "reference_role": "calibration_reference_only",
                    "review_status": "candidate_requires_manual_review",
                    "dataset_ref": {"provider": "AI-Hub", "dataset_key": "597"},
                    "scenario_summary": "AI-Hub label reference",
                    "structured_facts": {"collision_partner_type": "vehicle"},
                    "reference_expectations": {
                        "direct_collision_partner_type": "vehicle",
                        "must_not_promote": ["pedestrian_as_direct_collision_target"],
                    },
                    "evaluation_focus": ["direct_collision_partner_type"],
                    "usage_policy": {
                        "agent_input_allowed": False,
                        "raw_video_commit_allowed": False,
                        "notes": "evaluation reference only",
                    },
                }
            ],
        },
    )

    result = validate_manifest(manifest_path)

    assert "reference_contains_agent_input_payload" in error_codes(result)


def test_aihub_label_conversion_keeps_reference_only_policy(tmp_path: Path) -> None:
    label_path = tmp_path / "TL_sample_vehicle.json"
    write_json(
        label_path,
        {
            "video": {
                "accident_object": "0",
                "traffic_accident_type": "car_to_car",
                "accident_place": "intersection",
                "accident_place_feature": "signal",
                "vehicle_a_progress_info": "left_turn",
                "vehicle_b_progress_info": "straight",
                "accident_negligence_rateA": "70",
                "accident_negligence_rateB": "30",
            }
        },
    )

    case = build_case(label_path, {"source.zip": "509999"}, {})

    assert case["source_type"] == "aihub_sample"
    assert case["reference_role"] == "calibration_reference_only"
    assert case["usage_policy"]["agent_input_allowed"] is False
    assert case["usage_policy"]["raw_video_commit_allowed"] is False
    assert "structured_facts" not in case
    assert "case_json" not in case
    assert case["reference_expectations"]["direct_collision_partner_type"] == "vehicle"
