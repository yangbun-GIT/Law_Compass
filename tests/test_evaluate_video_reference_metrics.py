from __future__ import annotations

from pathlib import Path

from scripts.evaluate_video_reference_metrics import aggregate, load_batch_samples, load_reference_cases, score_sample


def test_reference_metrics_ignore_unpromoted_candidate_target_pollution() -> None:
    sample = {
        "name": "candidate-not-promoted",
        "frame_observation_count": 8,
        "field_metrics": [
            {
                "field": "collision_partner_type",
                "value": "vehicle",
                "applied": True,
                "confirmed": False,
                "in_fact_patch": True,
            },
            {
                "field": "primary_collision_target",
                "value": "pedestrian_candidate",
                "applied": False,
                "confirmed": False,
                "in_fact_patch": False,
            },
            {
                "field": "intersection",
                "value": True,
                "applied": False,
                "confirmed": False,
                "in_fact_patch": False,
            },
        ],
        "expert_guidance": {"basis": [], "legal_points": [], "legal_limits": []},
    }
    reference = {
        "id": "candidate-not-promoted",
        "reference_expectations": {
            "direct_collision_partner_type": "vehicle",
            "must_not_promote": ["pedestrian_candidate"],
            "expected_context": ["intersection_context"],
        },
    }

    scored = score_sample(sample, reference)

    assert scored["actual_direct_collision_partner_type"] == "vehicle"
    assert scored["direct_collision_target_passed"] is True
    assert scored["context_pollution"] is False
    assert scored["matched_expected_context"] == ["intersection_context"]
    assert scored["missing_expected_context"] == []
    assert scored["evidence_mismatch"] is False


def test_reference_metrics_do_not_treat_unconfirmed_candidate_as_direct_target() -> None:
    sample = {
        "name": "candidate-only",
        "frame_observation_count": 4,
        "field_metrics": [
            {
                "field": "primary_collision_target",
                "value": "bicycle_candidate",
                "applied": False,
                "confirmed": False,
                "in_fact_patch": False,
            }
        ],
        "expert_guidance": {"basis": [], "legal_points": [], "legal_limits": []},
    }
    reference = {
        "id": "candidate-only",
        "reference_expectations": {
            "direct_collision_partner_type": "bicycle",
            "must_not_promote": ["bicycle_candidate"],
        },
    }

    scored = score_sample(sample, reference)

    assert scored["actual_direct_collision_partner_type"] == "unknown"
    assert scored["direct_collision_target_passed"] is False
    assert scored["context_pollution"] is False


def test_reference_metrics_fixture_covers_p9_3_regression_axes() -> None:
    root = Path(__file__).resolve().parents[1]
    references = load_reference_cases(root / "tests/fixtures/video_accuracy/reference_metrics_manifest.json")
    samples = load_batch_samples(root / "tests/fixtures/video_accuracy/reference_metrics_batch_aggregate.json")
    required_ids = {
        "metrics_centerline_vehicle",
        "metrics_intersection_signal_unknown",
        "metrics_right_turn_front_vehicle_stop",
        "metrics_unlit_stopped_vehicle_highway",
        "metrics_non_contact_bicycle_trigger_rear_bus",
        "metrics_aihub_motorcycle_intersection",
        "metrics_aihub_bicycle_straight",
        "metrics_pedestrian_background_vehicle_collision",
    }

    assert required_ids.issubset(references)
    assert required_ids.issubset({sample["name"] for sample in samples})

    scored = [score_sample(sample, references.get(sample["name"])) for sample in samples]
    summary = aggregate(
        scored,
        {
            "direct_collision_target_accuracy": 0.8,
            "accident_party_accuracy": 0.8,
            "context_pollution_rate_max": 0.0,
            "zero_observation_rate_max": 0.2,
            "evidence_mismatch_rate_max": 0.2,
            "conditional_branch_coverage": 0.8,
        },
    )

    assert summary["sample_count"] >= 8
    assert summary["direct_collision_target_accuracy"] == 1.0
    assert summary["accident_party_accuracy"] == 1.0
    assert summary["context_pollution_rate"] == 0.0
    assert summary["zero_observation_rate"] == 0.0
    assert summary["evidence_mismatch_rate"] == 0.0
    assert summary["conditional_branch_coverage"] == 1.0
    assert summary["status"] == "passed"
