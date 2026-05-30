import pytest

from app.services.agent_contracts import AgentTaskRuntimePacket
from app.services.agent_task_packets import attach_agent_task_packets
from app.services.planner import build_task_plan


def test_runtime_packet_rejects_sensitive_metadata():
    with pytest.raises(ValueError):
        AgentTaskRuntimePacket(
            task_id="input_normalization",
            task_type="input_normalization",
            status="succeeded",
            packet={"raw_user_text": "do not expose"},
        )


def test_attach_agent_task_packets_updates_plan_statuses_without_raw_text():
    plan = build_task_plan(
        description_text="신호대기 중 후방 차량 추돌",
        structured_facts={"stopped": True},
        case_id="case-packet",
    ).model_dump()
    output = {
        "agent_plan": plan,
        "structured_facts": {"stopped": True, "missing_fields": []},
        "scenario_type": "rear_end_collision",
        "accident_party_type": "car_vs_car",
        "evidence": [{"title": "safe"}],
        "legal_evidence": [{"title": "safe"}],
        "knia_evidence": [{"title": "safe"}],
        "combined_evidence": [{"title": "safe"}],
        "knia_matches": [{"chart_no": "차41-1"}],
        "knia_primary_match": {"chart_no": "차41-1"},
        "fault_ratio": {"my": 0, "other": 100, "fault_estimate_source": "scenario_default"},
        "legal_liability": {"evidence_support_level": "partial"},
        "insurance_guide": {"evidence_support_level": "partial"},
        "action_plan": ["보험 접수"],
        "presentation_policy": {"finality": "reference_only"},
        "disclaimers": ["참고"],
        "evidence_audit": {
            "evidence_quality": "medium",
            "scenario_evidence_coverage": {"coverage_level": "medium", "missing_requirements": []},
        },
        "agent_judgment": {
            "must_not_present_as_final": True,
            "stage_statuses": [
                {"name": "scenario_classification", "status": "evidence_supported", "summary": "ok"},
                {"name": "evidence_retrieval", "status": "evidence_supported", "summary": "ok"},
                {"name": "knia_fault_basis", "status": "evidence_supported", "summary": "ok"},
                {"name": "fault_ratio_analysis", "status": "evidence_supported", "summary": "ok"},
                {"name": "criminal_liability_analysis", "status": "needs_review", "summary": "review"},
                {"name": "insurance_guidance", "status": "needs_review", "summary": "review"},
                {"name": "action_plan", "status": "evidence_supported", "summary": "ok"},
            ],
        },
        "model_info": {},
    }

    attach_agent_task_packets(output)

    packets = output["agent_task_packets"]
    assert packets["version"] == "agent-task-packets-v1"
    assert packets["task_count"] == len(output["agent_plan"]["tasks"])
    assert packets["status_counts"]["succeeded"] >= 5
    plan_statuses = {task["task_id"]: task["status"] for task in output["agent_plan"]["tasks"]}
    assert plan_statuses["input_normalization"] == "succeeded"
    assert plan_statuses["fault_ratio"] == "succeeded"
    assert plan_statuses["criminal_liability"] == "needs_review"
    assert "신호대기 중 후방 차량 추돌" not in str(packets)
