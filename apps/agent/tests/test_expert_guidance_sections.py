from app.services.expert_guidance_sections import build_expert_guidance_sections
from app.services.static_legal_fallback import retrieve_static_legal_chunks


def test_builds_user_safe_legal_and_insurance_guidance():
    sections = build_expert_guidance_sections(
        scenario={"scenario_type": "rear_end_collision", "accident_party_label": "차대차 사고"},
        facts={"stopped": True, "opponent_behavior": "rear_collision"},
        legal_analysis={
            "legal_issue_summary": "뒤차의 안전거리 유지 의무와 정차 사유를 함께 봅니다.",
            "required_facts": ["정차 사유", "충돌 직전 속도"],
        },
        fault_ratio={
            "my": 20,
            "other": 80,
            "key_factors": ["정차 여부", "후방 추돌 여부"],
        },
        legal_liability={
            "criminal_risk_level": "low",
            "checklist": ["인명피해 여부", "사고 후 조치 여부"],
        },
        insurance_guide={
            "summary": "대물 접수와 과실비율 협의를 준비합니다.",
            "steps": ["보험사 사고 접수", "블랙박스 원본 제출"],
            "required_documents": ["블랙박스 원본", "차량 파손 사진"],
        },
        evidence=[
            {
                "chunk_id": "secret-internal-id",
                "source_type": "knia_fault_standard",
                "title": "후방 추돌 기준",
                "related_reason": "정차 차량 후방 추돌 기준과 연결됩니다.",
            },
            {
                "chunk_id": "law-secret",
                "law_name": "도로교통법",
                "article_title": "안전거리 유지",
                "plain_summary": "뒤차는 앞차와 안전거리를 유지해야 합니다.",
            },
        ],
        evidence_audit={"scenario_evidence_coverage": {"coverage_level": "high"}},
        claim_evidence={"coverage_level": "high", "unsupported_claim_count": 0, "weak_claim_count": 0},
        input_requirements={"questions": [{"field": "stopped", "question": "정차 중이었나요?"}]},
        reflection_loop={},
    )

    assert sections["version"] == "expert-guidance-sections-v1"
    assert sections["status"] == "needs_more_facts"
    assert sections["legal_prediction"]["fault_range_label"] == "내 책임 10~30% / 상대 70~90% 참고"
    assert sections["insurance_prediction"]["expected_steps"] == ["보험사 사고 접수", "블랙박스 원본 제출"]
    assert sections["missing_facts"]["items"][0] == "정차 중이었나요?"
    text = str(sections)
    assert "chunk_id" not in text
    assert "secret-internal-id" not in text


def test_basis_summary_keeps_legal_basis_when_knia_items_are_first():
    sections = build_expert_guidance_sections(
        scenario={"scenario_type": "parking_or_stopped_vehicle_accident"},
        facts={"centerline_crossed": True, "centerline_cross_reason": "parked vehicle obstacle avoidance"},
        legal_analysis={},
        fault_ratio={"my": 30, "other": 70},
        legal_liability={"criminal_risk_level": "medium"},
        insurance_guide={},
        evidence=[
            {"source_type": "knia_reference", "title": "KNIA centerline reference"},
            {"source_type": "knia_reference", "title": "KNIA stopped vehicle reference"},
            {"source_type": "knia_reference", "title": "KNIA avoidability reference"},
            {
                "source_type": "legal_reference",
                "title": "중앙선 장애물 회피 사고 법률 검토 기준",
                "law_name": "도로교통법",
            },
        ],
        evidence_audit={},
        claim_evidence={"coverage_level": "high", "unsupported_claim_count": 0, "weak_claim_count": 0},
        input_requirements={},
        reflection_loop={},
    )

    basis_titles = [item["title"] for item in sections["legal_prediction"]["basis"]]
    assert "중앙선 장애물 회피 사고 법률 검토 기준" in basis_titles[:4]
    assert "KNIA centerline reference" in basis_titles[:4]


def test_basis_summary_drops_unrelated_extra_basis_for_signal_cases():
    sections = build_expert_guidance_sections(
        scenario={"scenario_type": "intersection_signal_violation", "accident_party_label": "signal transition crash"},
        facts={"accident_type": "left turn signal transition", "opponent_signal": "unknown"},
        legal_analysis={"legal_issue_summary": "signal transition and CCTV verification are key facts"},
        fault_ratio={"my": 80, "other": 20, "key_factors": ["signal transition", "CCTV verification"]},
        legal_liability={"criminal_risk_level": "medium"},
        insurance_guide={},
        evidence=[
            {
                "source_type": "legal_reference",
                "title": "Signal transition and CCTV verification guide",
                "related_reason": "signal transition, opponent signal, and CCTV are decisive facts.",
            },
            {
                "source_type": "knia_reference",
                "title": "Intersection signal fault ratio guide",
                "related_reason": "intersection and signal violation fault ratio reference.",
            },
            {
                "source_type": "legal_reference",
                "title": "Lane change legal duty guide",
                "related_reason": "lane change, merge, and side collision duty review.",
            },
        ],
        evidence_audit={},
        claim_evidence={"coverage_level": "high", "unsupported_claim_count": 0, "weak_claim_count": 0},
        input_requirements={},
        reflection_loop={},
    )

    basis_titles = [item["title"] for item in sections["legal_prediction"]["basis"]]
    assert "Signal transition and CCTV verification guide" in basis_titles
    assert "Intersection signal fault ratio guide" in basis_titles
    assert "Lane change legal duty guide" not in basis_titles


def test_basis_summary_keeps_crosswalk_front_stop_rear_end_basis():
    sections = build_expert_guidance_sections(
        scenario={"scenario_type": "rear_end_collision", "accident_party_label": "crosswalk rear-end"},
        facts={"crosswalk_nearby": True, "front_vehicle_stopped": True},
        legal_analysis={"legal_issue_summary": "rear-end crash after front vehicle stopped before crosswalk"},
        fault_ratio={"my": 95, "other": 5, "key_factors": ["front vehicle stop reason", "crosswalk", "pedestrian signal"]},
        legal_liability={"criminal_risk_level": "low"},
        insurance_guide={},
        evidence=[
            {
                "source_type": "knia_reference",
                "title": "Rear-end default safe distance guide",
                "related_reason": "rear-end safe distance and stopped vehicle reference.",
            },
            {
                "source_type": "knia_reference",
                "title": "Crosswalk front vehicle stop reason and rear-end fault guide",
                "related_reason": "front vehicle stop reason, crosswalk, pedestrian signal, safe distance, and rear-end collision are directly relevant.",
            },
            {
                "source_type": "legal_reference",
                "title": "Crosswalk pedestrian signal duty guide",
                "related_reason": "crosswalk, pedestrian signal, and front vehicle stop reason should be checked.",
            },
        ],
        evidence_audit={},
        claim_evidence={"coverage_level": "high", "unsupported_claim_count": 0, "weak_claim_count": 0},
        input_requirements={},
        reflection_loop={},
    )

    basis_titles = [item["title"] for item in sections["legal_prediction"]["basis"]]
    assert "Crosswalk front vehicle stop reason and rear-end fault guide" in basis_titles


def test_false_pedestrian_video_fact_does_not_boost_pedestrian_basis():
    sections = build_expert_guidance_sections(
        scenario={"scenario_type": "general_collision", "accident_party_label": "vehicle collision"},
        facts={
            "collision_partner_type": "vehicle",
            "primary_collision_target": "vehicle",
            "pedestrian_visible": False,
        },
        legal_analysis={"legal_issue_summary": "vehicle collision facts and impact point are key"},
        fault_ratio={"my": 40, "other": 60, "key_factors": ["vehicle collision", "impact point"]},
        legal_liability={"criminal_risk_level": "low"},
        insurance_guide={},
        evidence=[
            {
                "source_type": "legal_reference",
                "title": "Crosswalk pedestrian duty guide",
                "related_reason": "pedestrian and crosswalk duty reference.",
            },
            {
                "source_type": "legal_reference",
                "title": "Vehicle collision impact point guide",
                "related_reason": "vehicle collision and impact point reference.",
            },
            {
                "source_type": "knia_reference",
                "title": "Vehicle to vehicle fault guide",
                "related_reason": "vehicle collision fault ratio reference.",
            },
        ],
        evidence_audit={},
        claim_evidence={"coverage_level": "high", "unsupported_claim_count": 0, "weak_claim_count": 0},
        input_requirements={},
        reflection_loop={},
    )

    basis_titles = [item["title"] for item in sections["legal_prediction"]["basis"]]
    assert "Vehicle collision impact point guide" in basis_titles[:2]
    assert "Crosswalk pedestrian duty guide" not in basis_titles[:2]


def test_basis_summary_keeps_non_contact_bicycle_trigger_basis():
    sections = build_expert_guidance_sections(
        scenario={"scenario_type": "bicycle_collision", "accident_party_label": "bicycle trigger rear-end"},
        facts={"bicycle_involved": True, "possible_trigger_vehicle": "bicycle", "time_gap_sec": 4},
        legal_analysis={"legal_issue_summary": "non-contact bicycle trigger followed by rear-end bus collision"},
        fault_ratio={"my": 20, "other": 80, "key_factors": ["non-contact bicycle trigger", "time gap", "sudden braking"]},
        legal_liability={"criminal_risk_level": "low"},
        insurance_guide={},
        evidence=[
            {
                "source_type": "knia_reference",
                "title": "후미추돌 과실비율 참고 기준",
                "related_reason": "rear-end safe distance reference.",
            },
            {
                "source_type": "knia_reference",
                "title": "Non-contact bicycle trigger and rear-end response guide",
                "related_reason": "non-contact bicycle trigger, rear-end bus collision, sudden braking, and time gap are directly relevant.",
            },
            {
                "source_type": "legal_reference",
                "title": "자전거 사고 주의의무 확인",
                "related_reason": "bicycle crash duty reference.",
            },
        ],
        evidence_audit={},
        claim_evidence={"coverage_level": "high", "unsupported_claim_count": 0, "weak_claim_count": 0},
        input_requirements={},
        reflection_loop={},
    )

    basis_titles = [item["title"] for item in sections["legal_prediction"]["basis"]]
    assert "Non-contact bicycle trigger and rear-end response guide" in basis_titles


def test_static_fallback_retrieves_legal_references_for_complex_reference_cases():
    centerline_chunks = retrieve_static_legal_chunks(
        "centerline obstacle avoidance oncoming vehicle collision parked vehicle",
        limit=5,
    )
    unlit_chunks = retrieve_static_legal_chunks(
        "unlit stopped vehicle night visibility speed limit avoidability analysis",
        limit=5,
    )

    assert any(item.get("source_type") == "legal_reference" for item in centerline_chunks)
    assert any(item.get("source_type") == "legal_reference" for item in unlit_chunks)


def test_narrows_fault_range_when_evidence_is_supported():
    sections = build_expert_guidance_sections(
        scenario={"scenario_type": "rear_end_collision"},
        facts={},
        legal_analysis={},
        fault_ratio={"my": 10, "other": 90},
        legal_liability={"criminal_risk_level": "low"},
        insurance_guide={},
        evidence=[],
        evidence_audit={},
        claim_evidence={"coverage_level": "high", "unsupported_claim_count": 0, "weak_claim_count": 0},
        input_requirements={},
        reflection_loop={},
    )

    assert sections["status"] == "evidence_supported_reference"
    assert sections["legal_prediction"]["fault_range_label"] == "내 책임 5~15% / 상대 85~95% 참고"
