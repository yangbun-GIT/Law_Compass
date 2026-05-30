from app.services.planner import build_safe_fallback_plan, build_task_plan


def test_text_only_plan_uses_existing_stage_order_without_video_tasks():
    plan = build_task_plan(
        description_text="신호대기 중 후방 추돌",
        structured_facts={"stopped": True},
        selected_keywords=["후방추돌"],
        case_id="case-1",
    )

    data = plan.model_dump()
    assert data["version"] == "agent-plan-v1"
    assert data["input_mode"] == "text_only"
    assert data["plan_status"] == "ready"
    assert data["execution_order"][0] == "input_normalization"
    assert "video_observation" not in data["execution_order"]
    assert "fact_arbitration" not in data["execution_order"]
    assert data["execution_order"][-1] == "presentation_policy"
    assert "신호대기 중 후방 추돌" not in str(data)


def test_video_only_plan_adds_observation_and_arbitration_tasks_safely():
    plan = build_task_plan(
        description_text="",
        video_metadata={
            "metadata": {
                "representative_frames": ["/frames/1.jpg", "/frames/2.jpg"],
                "observations": [{"field": "collision_point_visible", "value": True}],
            }
        },
        case_id="case-2",
        upload_id="upload-2",
    )

    data = plan.model_dump()
    assert data["input_mode"] == "video_only"
    assert data["execution_order"][:3] == ["input_normalization", "video_observation", "fact_arbitration"]
    video_task = next(task for task in data["tasks"] if task["task_id"] == "video_observation")
    assert video_task["required_tools"] == ["video_frame_analysis_adapter"]
    assert "representative_frame_count=2" in str(video_task["input_refs"])
    assert "collision_point_visible" not in str(data)


def test_followup_plan_uses_bounded_replan_policy():
    plan = build_task_plan(
        description_text="기존 사고 보완",
        structured_facts={
            "_followup_iteration": 1,
            "_followup_answered_fields": ["injury", "stopped"],
            "_followup_unresolved_fields": ["opponent_signal"],
        },
        case_id="case-3",
    )

    data = plan.model_dump()
    assert data["input_mode"] == "followup_reanalysis"
    assert data["replan_policy"] == "bounded_on_blocker"
    assert any(ref["ref_type"] == "questionnaire_answer" for task in data["tasks"] for ref in task["input_refs"])


def test_admin_diagnostic_plan_marks_creator():
    plan = build_task_plan(
        description_text="관리자 진단",
        structured_facts={"accident_party_type": "car_vs_car"},
        input_mode="admin_diagnostic",
        case_id="case-admin",
    )

    data = plan.model_dump()
    assert data["created_by"] == "admin_diagnostic"
    assert data["input_mode"] == "admin_diagnostic"


def test_safe_fallback_plan_is_blocked_but_contract_valid():
    plan = build_safe_fallback_plan(error=RuntimeError("bad planner"), input_mode="text_only", case_id="case-4")

    data = plan.model_dump()
    assert data["plan_status"] == "safe_fallback"
    assert data["tasks"][0]["status"] == "blocked"
    assert data["failure_observations"][0]["type"] == "agent_plan_creation_failed"
