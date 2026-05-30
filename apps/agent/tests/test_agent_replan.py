from app.services.agent_replan import MAX_REPLAN_ITERATIONS, attach_agent_replan


def test_replan_not_needed_when_no_allowed_blocker():
    output = {
        "agent_judgment": {"blocking_reasons": []},
        "agent_goal_result": {"conflict_packets": []},
        "reflection_loop": {"iterations_used": 0},
        "agent_plan": {"replan_policy": "none"},
    }

    attach_agent_replan(output)

    assert output["agent_replan"]["status"] == "not_needed"
    assert output["agent_replan"]["proposed_tasks"] == []
    assert output["agent_plan"]["replan_summary"]["status"] == "not_needed"


def test_replan_proposes_only_allowed_bounded_tasks():
    output = {
        "agent_judgment": {"blocking_reasons": ["required_evidence_not_ready", "unsupported_claims_present"]},
        "agent_goal_result": {
            "conflict_packets": [
                {"reason_code": "video_fact_not_directly_applied", "conflict_type": "video_user_fact_conflict"}
            ]
        },
        "fact_arbitration": {"held_video_fields": ["collision_target"]},
        "reflection_loop": {"iterations_used": 0},
        "agent_plan": {"replan_policy": "none"},
    }

    attach_agent_replan(output)

    replan = output["agent_replan"]
    task_ids = {task["task_id"] for task in replan["proposed_tasks"]}
    reason_codes = {reason["reason_code"] for reason in replan["replan_reasons"]}
    assert replan["status"] == "proposed"
    assert replan["max_iterations"] == MAX_REPLAN_ITERATIONS
    assert "replan_evidence_retrieval" in task_ids
    assert "replan_fact_arbitration" in task_ids
    assert "unsupported_claims_present" not in reason_codes
    assert output["agent_plan"]["replan_policy"] == "bounded_on_blocker"


def test_replan_exhausts_after_one_iteration():
    output = {
        "agent_judgment": {"blocking_reasons": ["knia_basis_missing_or_incomplete"]},
        "agent_goal_result": {"conflict_packets": []},
        "reflection_loop": {"iterations_used": 1},
        "agent_plan": {"replan_policy": "bounded_on_blocker"},
    }

    attach_agent_replan(output)

    assert output["agent_replan"]["status"] == "exhausted_reference_only"
    assert output["agent_replan"]["replan_allowed"] is False
    assert output["agent_replan"]["next_action"] == "present_reference_only"
