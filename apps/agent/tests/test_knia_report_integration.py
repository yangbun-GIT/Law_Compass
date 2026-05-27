from app.services.elderly_friendly.report_simplifier import build_elderly_friendly_report


def _base_result(**overrides):
    result = {
        "scenario_type": "rear_end_collision",
        "accident_summary": "정차 중 뒤차가 추돌한 사고",
        "structured_facts": {"scenario_type": "rear_end_collision"},
        "fault_ratio": {"my": 0, "other": 100},
        "legal_liability": {},
        "insurance_guide": {},
        "evidence": [],
        "knia_matches": [],
        "knia_primary_match": None,
    }
    result.update(overrides)
    return result


def test_knia_video_url_fallback_builds_external_link_card(monkeypatch):
    def fake_get_chart(_self, chart_no, chart_type="1"):
        return {
            "chart_no": chart_no,
            "chart_type": chart_type,
            "title": "임의 후미추돌 기준",
            "accident_summary": "정차 차량을 뒤차가 추돌한 사고",
            "source_url": "https://accident.knia.or.kr/myaccident-content?chartNo=TEST-REAR-1",
            "source_detail_url": "https://accident.knia.or.kr/myaccident-content?chartNo=TEST-REAR-1",
            "thumbnail_url": "https://accident.knia.or.kr/images/common/logo_test.jpg",
            "video_url": "https://accident.knia.or.kr/video/test-rear-1.mp4",
            "media_embed_url": "https://accident.knia.or.kr/embed/test-rear-1",
            "media_provider": "external_url",
            "license_status": "source_link_only",
        }

    monkeypatch.setattr("app.services.knia.knia_repository.KniaRepository.get_chart", fake_get_chart)

    report = build_elderly_friendly_report(_base_result(
        knia_matches=[{"chart_no": "TEST-REAR-1", "title": "임의 후미추돌 기준"}],
    ))

    card = report["related_knia_video_card"]
    assert card["source_url"] == "https://accident.knia.or.kr/video/test-rear-1.mp4"
    assert card["video_url"] == "https://accident.knia.or.kr/video/test-rear-1.mp4"
    assert card["button_label"] == "KNIA 관련 영상 보기"
    assert card["display_mode"] == "external_link"
    assert "과실비율정보포털 원본 링크" in card["notice"]
    assert "embed_url" not in card
    assert card.get("thumbnail_url") is None


def test_knia_source_url_fallback_builds_source_button(monkeypatch):
    def fake_get_chart(_self, chart_no, chart_type="1"):
        return {
            "chart_no": chart_no,
            "chart_type": chart_type,
            "title": "임의 후방추돌 기준",
            "accident_summary": "선행 차량을 뒤차가 추돌한 사고",
            "source_url": "https://accident.knia.or.kr/myaccident-content?chartNo=TEST-REAR-2",
            "source_detail_url": "https://accident.knia.or.kr/myaccident-content?chartNo=TEST-REAR-2&chartType=1",
            "video_url": None,
            "media_embed_url": "https://accident.knia.or.kr/embed/test-rear-2",
            "media_provider": "external_url",
            "license_status": "source_link_only",
        }

    monkeypatch.setattr("app.services.knia.knia_repository.KniaRepository.get_chart", fake_get_chart)

    report = build_elderly_friendly_report(_base_result(
        knia_matches=[{"chart_no": "TEST-REAR-2", "title": "임의 후방추돌 기준"}],
    ))

    card = report["related_knia_video_card"]
    assert card["source_url"] == "https://accident.knia.or.kr/myaccident-content?chartNo=TEST-REAR-2&chartType=1"
    assert card["button_label"] == "KNIA 원문 기준 보기"
    assert card["display_mode"] == "external_link"
    assert "embed_url" not in card


def test_rejected_mismatch_knia_candidate_is_not_display_representative(monkeypatch):
    def fake_get_chart(_self, chart_no, chart_type="1"):
        return {
            "chart_no": chart_no,
            "chart_type": chart_type,
            "title": "호환되는 후미추돌 기준",
            "accident_summary": "정차 차량 후미추돌",
            "source_url": f"https://accident.knia.or.kr/myaccident-content?chartNo={chart_no}",
            "source_detail_url": f"https://accident.knia.or.kr/myaccident-content?chartNo={chart_no}&chartType=1",
            "video_url": None,
            "media_provider": "external_url",
            "license_status": "source_link_only",
        }

    monkeypatch.setattr("app.services.knia.knia_repository.KniaRepository.get_chart", fake_get_chart)

    report = build_elderly_friendly_report(_base_result(
        knia_matches=[
            {
                "chart_no": "TEST-BAD-1",
                "title": "교차로 직진 대 좌회전",
                "source_detail_url": "https://accident.knia.or.kr/myaccident-content?chartNo=TEST-BAD-1",
                "exclusion_reason": "knia_basis_mismatch",
            },
            {"chart_no": "TEST-REAR-3", "title": "호환되는 후미추돌 기준"},
        ],
    ))

    card = report["related_knia_video_card"]
    assert card["chart_no"] == "TEST-REAR-3"
    assert "TEST-BAD-1" not in str(card)
