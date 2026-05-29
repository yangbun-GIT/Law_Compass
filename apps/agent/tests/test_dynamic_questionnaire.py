from app.services.analysis_modes import build_analysis_mode_contract, normalize_analysis_mode
from app.services.dynamic_questionnaire import build_dynamic_questionnaire


def test_rear_end_guided_questions_are_plain_and_include_unknown_choice():
    questionnaire = build_dynamic_questionnaire(
        scenario_type="rear_end_collision",
        accident_party_type="car_vs_car",
        analysis_mode="fault_ratio_focused",
        description_text="빨간불에 정차 중 뒤차가 추돌했습니다.",
        structured_facts={"stopped": True},
    )

    questions = questionnaire["questions"]
    text = " ".join(f"{q['plain_question']} {q['why_it_matters']}" for q in questions)

    assert questionnaire["version"] == "agent-dynamic-questionnaire-v1"
    assert any(q["question_id"] == "rear_end.stop_reason" for q in questions)
    assert "급정거" in text
    assert "브레이크등" in text
    assert "왜" in text or "이유" in text
    assert all(any(choice["label"] == "잘 모르겠어요" for choice in q["choices"]) for q in questions)


def test_signal_violation_questionnaire_is_distinct_from_rear_end():
    questionnaire = build_dynamic_questionnaire(
        scenario_type="intersection_signal_violation",
        accident_party_type="car_vs_car",
        analysis_mode="quick_summary",
        description_text="제가 빨간불에 교차로로 진입했고 정상 신호로 직진하던 상대 차량과 충돌했습니다.",
    )

    question_ids = {item["question_id"] for item in questionnaire["questions"]}

    assert "signal.who_entered_red" in question_ids
    assert not any(item.startswith("rear_end.") for item in question_ids)


def test_analysis_mode_aliases_keep_legacy_api_values_but_ui_contract_is_guided():
    assert normalize_analysis_mode("fault-focused") == "user_friendly"
    assert normalize_analysis_mode("criminal-liability-focused") == "expert"
    assert normalize_analysis_mode("evidence-review") == "expert"

    quick = build_analysis_mode_contract("quick_summary")
    assert "long_legal_basis" in quick["hidden_sections"]
    assert quick["mode"] == "user_friendly"
    assert quick["compact"] is True
