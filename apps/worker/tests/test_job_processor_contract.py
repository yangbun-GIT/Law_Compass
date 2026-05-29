import unittest

from worker.job_processor import (
    build_agent_video_request,
    build_analysis_result_values,
    build_frame_analysis_context,
    build_video_analyze_payload,
    _merge_frame_observations,
)
from worker.video_preprocess import VIDEO_PREPROCESS_CONTRACT_VERSION


class WorkerJobProcessorContractTest(unittest.TestCase):
    def setUp(self):
        self.row = (
            "job-1",
            "case-1",
            "upload-1",
            "user-1",
            {},
        )

    def test_video_preprocess_enqueues_canonical_video_analyze_payload(self):
        payload = {"ai_profile": "custom-profile", "specialist_roles": ["traffic_law"]}
        case_inputs = (
            {"accident_type": "rear_end_collision", "stopped": True},
            ["후방추돌", "안전거리"],
            "rear-end-focused",
        )

        result = build_video_analyze_payload(self.row, payload, case_inputs)

        self.assertEqual(result["case_id"], "case-1")
        self.assertEqual(result["upload_id"], "upload-1")
        self.assertEqual(result["ai_profile"], "custom-profile")
        self.assertEqual(result["specialist_roles"], ["traffic_law"])
        self.assertEqual(result["routing_reason"], "auto_after_local_preprocess")
        self.assertEqual(result["structured_facts"]["stopped"], True)
        self.assertEqual(result["selected_keywords"], ["후방추돌", "안전거리"])
        self.assertEqual(result["analysis_mode"], "rear-end-focused")

    def test_frame_analysis_context_uses_case_facts_as_visual_focus_only(self):
        metadata = {"duration_sec": 8.5, "width": 1280, "height": 720, "fps": 30}
        case_inputs = (
            {
                "accident_type": "rear_end_collision",
                "stopped": True,
                "opponent_behavior": "rear_collision",
                "free_text_note": "must not be copied into frame prompt context",
            },
            ["rear impact", "stationary"],
            "fault_ratio",
        )

        result = build_frame_analysis_context(self.row, metadata, case_inputs)

        self.assertEqual(result["case_id"], "case-1")
        self.assertEqual(result["upload_id"], "upload-1")
        self.assertTrue(result["user_context_is_visual_focus_only"])
        self.assertEqual(result["visual_focus"]["accident_type"], "rear_end_collision")
        self.assertEqual(result["visual_focus"]["stopped"], True)
        self.assertEqual(result["visual_focus"]["opponent_behavior"], "rear_collision")
        self.assertNotIn("free_text_note", result["visual_focus"])
        self.assertEqual(result["selected_keywords"], ["rear impact", "stationary"])

    def test_agent_video_request_preserves_preprocess_contract_and_summary_inputs(self):
        payload = {
            "ai_profile": "default_vehicle_collision",
            "specialist_roles": ["fault_ratio"],
            "routing_reason": "auto_after_local_preprocess",
            "structured_facts": {"stopped": True, "opponent_behavior": "rear_collision"},
            "selected_keywords": ["후방추돌"],
            "analysis_mode": "rear-end-focused",
            "video_metadata": {"manual_note": "driver supplied short clip"},
        }
        case_row = ("정차 중 추돌", "신호대기 중 뒤차가 충돌했습니다.")
        upload_metadata = {
            "duration_sec": 6.5,
            "preprocess_summary": "Local video verified. duration=6.5s, frames=10.",
            "observations": [{"field": "stopped", "value": True}],
        }
        upload_row = (upload_metadata, "accident.mp4", "ready")

        result = build_agent_video_request(self.row, payload, case_row, upload_row)

        self.assertEqual(result["case_id"], "case-1")
        self.assertEqual(result["user_id"], "user-1")
        self.assertEqual(result["upload_id"], "upload-1")
        self.assertEqual(result["analysis_mode"], "rear-end-focused")
        self.assertEqual(result["video_metadata"]["preprocess_contract_version"], VIDEO_PREPROCESS_CONTRACT_VERSION)
        self.assertEqual(result["video_metadata"]["upload_status"], "ready")
        self.assertEqual(result["video_metadata"]["file_name"], "accident.mp4")
        self.assertEqual(result["video_metadata"]["metadata"], upload_metadata)
        self.assertEqual(result["video_metadata"]["preprocess_payload"], {"manual_note": "driver supplied short clip"})
        self.assertIn("Local video verified", result["preprocessed_summary"])
        self.assertIn("정차 중 추돌", result["preprocessed_summary"])
        self.assertIn("후방추돌", result["preprocessed_summary"])
        self.assertIn("rear_collision", result["preprocessed_summary"])
        self.assertIn("routing_reason:auto_after_local_preprocess", result["preprocessed_summary"])

    def test_frame_observation_merge_preserves_openai_and_yolo_candidates(self):
        result = _merge_frame_observations(
            {"observations": [{"field": "collision_partner_type", "value": "vehicle", "source": "frame_analysis:openai"}]},
            {"observations": [{"field": "primary_collision_target", "value": "vehicle_candidate", "source": "vision_model:yolo"}]},
            {"observations": ["invalid"]},
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["source"], "frame_analysis:openai")
        self.assertEqual(result[1]["source"], "vision_model:yolo")

    def test_frame_observation_merge_demotes_openai_non_vehicle_direct_without_yolo_sequence_support(self):
        result = _merge_frame_observations(
            {
                "observations": [
                    {
                        "field": "direct_collision_partner_type",
                        "value": "pedestrian",
                        "confidence": 0.88,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_004.jpg", "frame_005.jpg", "frame_006.jpg"],
                    }
                ]
            },
            {
                "observations": [
                    {
                        "field": "primary_collision_target",
                        "value": "pedestrian_candidate",
                        "confidence": 0.72,
                        "source": "vision_model:yolo",
                        "frame_refs": ["frame_001.jpg", "frame_002.jpg"],
                    }
                ]
            },
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["field"], "primary_collision_target")
        self.assertEqual(result[0]["value"], "pedestrian_candidate")
        self.assertLess(result[0]["confidence"], 0.7)
        self.assertIn("requires_yolo_sequence_support", result[0]["reason"])

    def test_frame_observation_merge_keeps_non_vehicle_direct_with_yolo_sequence_support(self):
        result = _merge_frame_observations(
            {
                "observations": [
                    {
                        "field": "direct_collision_partner_type",
                        "value": "bicycle",
                        "confidence": 0.88,
                        "source": "frame_analysis:openai",
                        "frame_refs": ["frame_004.jpg", "frame_005.jpg", "frame_006.jpg"],
                    }
                ]
            },
            {
                "observations": [
                    {
                        "field": "direct_collision_partner_type",
                        "value": "bicycle",
                        "confidence": 0.8,
                        "source": "vision_model:yolo_sequence",
                        "frame_refs": ["frame_004.jpg", "frame_005.jpg"],
                    }
                ]
            },
        )

        by_source = {item["source"]: item for item in result}
        self.assertEqual(by_source["frame_analysis:openai"]["field"], "direct_collision_partner_type")
        self.assertEqual(by_source["vision_model:yolo_sequence"]["field"], "direct_collision_partner_type")

    def test_analysis_result_values_keep_result_contract_fields(self):
        response = {
            "evidence": [{"chunk_id": "chunk-1"}, {"title": "no chunk"}],
            "uncertainty": {"level": "low"},
            "model_info": {"policy": "deterministic"},
            "structured_facts": {"stopped": True},
            "recommended_keywords": ["후방추돌"],
            "suggested_next_inputs": ["블랙박스 원본"],
            "elderly_friendly_report": {"summary": "요약"},
            "legal_analysis": {"risk_flags": ["safe_distance"]},
            "legal_liability": {"risk_flags": []},
            "scenario_type": "rear_end_collision",
            "recommended_specialists": ["traffic_law"],
            "evidence_audit": {"coverage": "ok"},
        }

        result = build_analysis_result_values(self.row, response, 3)

        self.assertEqual(result["case_id"], "case-1")
        self.assertEqual(result["owner_user_id"], "user-1")
        self.assertEqual(result["version"], 3)
        self.assertEqual(result["result"], response)
        self.assertEqual(result["used_evidence_ids"], ["chunk-1"])
        self.assertEqual(result["legal_risk_flags"], ["safe_distance"])
        self.assertEqual(result["persona_outputs"], {"analysts": ["traffic_law"]})
        self.assertEqual(result["evidence_audit"], {"coverage": "ok"})


if __name__ == "__main__":
    unittest.main()
