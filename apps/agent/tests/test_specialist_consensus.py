from app.services.specialist_consensus import (
    VERSION,
    attach_specialist_consensus,
    build_specialist_consensus,
)


def test_specialist_consensus_maps_knia_axis_conflict_to_blocking_packet():
    output = {
        "agent_goal_result": {
            "conflict_packets": [
                {
                    "conflict_type": "law_fault_axis_mismatch",
                    "severity": "block",
                    "status": "blocked_for_consistency",
                    "reason_code": "knia_party_type_mismatch",
                    "source_refs": ["accident_party_type", "knia_primary_match.major_party_type"],
                }
            ]
        }
    }

    consensus = build_specialist_consensus(output)

    assert consensus["version"] == VERSION
    assert consensus["status"] == "blocked_for_consistency"
    assert consensus["conflict_count"] == 1
    assert consensus["conflicts"][0]["conflict_type"] == "knia_standard_conflict"
    assert consensus["resolution"]["must_not_use_flat_50_50_fallback"] is True
    assert consensus["resolution"]["next_required_inputs"] == ["accident_axis_or_knia_basis_confirmation"]
    assert consensus["safe_metadata_only"] is True


def test_specialist_consensus_requires_conditional_result_for_uncertain_signal_fault_branches():
    output = {
        "scenario_type": "intersection_signal_violation",
        "structured_facts": {
            "signal_state": "황색에서 적색으로 변경",
            "opponent_signal_visible": False,
        },
        "fault_ratio": {
            "conditional_outcomes": [
                {"label": "상대 신호 녹색", "my": 80, "other": 20},
                {"label": "상대 신호 적색", "my": 20, "other": 80},
            ]
        },
    }

    output = attach_specialist_consensus(output)
    consensus = output["specialist_consensus"]

    assert consensus["status"] == "needs_conditionals"
    assert consensus["conditional_conflict_count"] == 1
    assert consensus["conflicts"][0]["conflict_type"] == "signal_status_conflict"
    assert consensus["resolution"]["answer_policy"] == "present_conditional_results_before_fault_ratio"
    assert "signal_status_confirmation" in consensus["resolution"]["next_required_inputs"]


def test_specialist_consensus_ready_when_no_conflicts_or_uncertainties():
    consensus = build_specialist_consensus(
        {
            "agent_goal_result": {"conflict_packets": []},
            "specialist_agent_results": {
                "results": [
                    {
                        "role_id": "fault_ratio_agent",
                        "claims": [{"claim_type": "fault_ratio_reference"}],
                        "uncertainties": [],
                        "unsupported_claims": [],
                    }
                ]
            },
        }
    )

    assert consensus["status"] == "ready"
    assert consensus["conflict_count"] == 0
    assert consensus["resolution"]["answer_policy"] == "single_reference_result_allowed"
    assert consensus["resolution"]["must_not_use_flat_50_50_fallback"] is False
