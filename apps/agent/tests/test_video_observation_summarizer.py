from app.services.video_observation_summarizer import summarize_client_pre_observations


def test_vehicle_tracks_create_car_vs_car_candidate_without_fault_or_chart():
    result = summarize_client_pre_observations({
        "source": "client_pre_observation",
        "provider": "google_mlkit",
        "observations": [
            {"field": "object_candidate", "value": "vehicle", "confidence": 0.8, "frame_time_sec": 1.0, "track_id": 1, "bbox": [0.1, 0.1, 0.3, 0.3]},
            {"field": "object_candidate", "value": "vehicle", "confidence": 0.82, "frame_time_sec": 2.0, "track_id": 1, "bbox": [0.2, 0.1, 0.4, 0.3]},
            {"field": "object_candidate", "value": "vehicle", "confidence": 0.76, "frame_time_sec": 1.2, "track_id": 2, "bbox": [0.6, 0.2, 0.8, 0.4]},
        ],
    })

    assert result["candidate_accident_context"]["possible_party_type"] == "car_vs_car"
    assert result["video_observation_summary"]["possible_context"]["possible_car_vs_car"] is True
    assert result["fault_ratio_result"]["judgment_status"] == "needs_review"
    assert result["fault_ratio_result"]["presentation_status"] == "reference_only"
    assert "chart_no" not in result["fault_ratio_result"]


def test_person_track_creates_person_candidate():
    result = summarize_client_pre_observations({
        "observations": [
            {"field": "object_candidate", "value": "person", "confidence": 0.7, "frame_time_sec": 1.0, "track_id": "p1", "bbox": [0.2, 0.2, 0.3, 0.5]},
        ],
    })

    assert result["candidate_accident_context"]["possible_party_type"] == "car_vs_person"
    assert result["video_observation_summary"]["possible_context"]["possible_car_vs_person"] is True


def test_motorcycle_track_is_not_collapsed_into_vehicle():
    result = summarize_client_pre_observations({
        "observations": [
            {"field": "object_candidate", "value": "motorcycle", "confidence": 0.75, "frame_time_sec": 1.0, "track_id": "m1", "bbox": [0.2, 0.2, 0.3, 0.5]},
        ],
    })

    assert result["observation_summary"]["motorcycles_detected"] == 1
    assert result["observation_summary"]["vehicles_detected"] == 0
    assert result["candidate_accident_context"]["possible_party_type"] == "car_vs_motorcycle"
    assert result["video_observation_summary"]["possible_context"]["possible_car_vs_motorcycle"] is True


def test_traffic_light_does_not_confirm_signal_violation():
    result = summarize_client_pre_observations({
        "observations": [
            {"field": "object_candidate", "value": "traffic_light", "confidence": 0.65, "frame_time_sec": 0.5, "bbox": [0.1, 0.1, 0.2, 0.2]},
        ],
    })

    assert result["video_observation_summary"]["possible_context"]["possible_signal_related"] is True
    assert result["fault_ratio_result"]["judgment_status"] == "needs_review"
    assert "signal_violation" not in result


def test_empty_observations_are_insufficient_video_only():
    result = summarize_client_pre_observations({"observations": []})

    assert result["analysis_readiness"]["can_infer_accident_context"] is False
    assert result["analysis_readiness"]["can_estimate_fault_ratio"] is False
    assert result["analysis_readiness"]["status"] == "insufficient_video_only"
    assert "충분한 객체 후보" in result["candidate_accident_context"]["missing_facts"]
