from app.services.agent_goal_aggregator import attach_agent_goal_result


def test_goal_aggregator_blocks_knia_party_axis_mismatch():
    output = _base_output()
    output["accident_party_type"] = "car_vs_car"
    output["knia_primary_match"] = {"major_party_type": "car_vs_person", "chart_no": "보1"}

    attach_agent_goal_result(output)

    result = output["agent_goal_result"]
    assert result["version"] == "agent-goal-result-v1"
    assert result["goal"]["status"] == "blocked"
    assert result["goal"]["finality"] == "blocked"
    assert result["conflict_packets"][0]["reason_code"] == "knia_party_type_mismatch"
    assert result["safe_metadata_only"] is True


def test_goal_aggregator_keeps_video_user_conflict_as_reference_only():
    output = _base_output()
    output["fact_arbitration"] = {
        "conflicts": [{"field": "accident_party_type"}],
        "held_video_fields": ["pedestrian_visible"],
        "pending_video_confirmations": ["collision_target"],
    }

    attach_agent_goal_result(output)

    result = output["agent_goal_result"]
    assert result["goal"]["status"] == "needs_review"
    assert result["goal"]["finality"] == "reference_only"
    assert result["goal"]["next_required_inputs"] == ["video_user_fact_confirmation"]
    assert any(packet["conflict_type"] == "video_user_fact_conflict" for packet in result["conflict_packets"])


def test_goal_aggregator_does_not_expose_raw_input_text():
    output = _base_output()
    raw_text = "신호대기 중 후방 차량 추돌"

    attach_agent_goal_result(output)

    assert raw_text not in str(output["agent_goal_result"])


def _base_output() -> dict:
    return {
        "scenario_type": "rear_end_collision",
        "accident_party_type": "car_vs_car",
        "fault_ratio": {"my": 0, "other": 100, "judgment_status": "evidence_supported"},
        "combined_evidence": [
            {"chunk_id": "static:knia:rear-end", "title": "양 차량 주행 중 후방 추돌", "source": "KNIA"}
        ],
        "agent_judgment": {
            "overall_status": "evidence_supported",
            "must_not_present_as_final": False,
            "blocking_reasons": [],
        },
        "agent_task_packets": {
            "version": "agent-task-packets-v1",
            "status_counts": {"succeeded": 4},
            "packets": [
                {"task_id": "evidence_retrieval", "status": "succeeded"},
                {"task_id": "knia_matching", "status": "succeeded"},
                {"task_id": "fault_ratio", "status": "succeeded", "packet": {"has_fault_numbers": True}},
            ],
        },
    }
