from __future__ import annotations

from scripts.evaluate_video_reference_metrics import score_sample


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
