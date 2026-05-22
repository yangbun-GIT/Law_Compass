import unittest

from app.services.reflection_loop import build_reflection_loop_result, build_requery_plan


class ReflectionLoopTests(unittest.TestCase):
    def test_requery_plan_uses_scenario_specific_korean_terms(self):
        plan = build_requery_plan(
            evidence_audit={
                "scenario_evidence_coverage": {
                    "missing_requirements": ["family:knia", "scenario_relevant_evidence"],
                    "decision_ready": False,
                }
            },
            input_requirements={"blocking_fields": []},
            scenario_type="rear_end_collision",
            description_text="정차 중 뒤에서 추돌당했습니다.",
        )

        self.assertTrue(plan["should_requery"])
        self.assertIn("후방추돌 과실비율", plan["query_terms"])
        self.assertIn("KNIA 과실비율 인정기준", plan["query_terms"])
        self.assertEqual(plan["next_action"], "requery_evidence")
        self.assertIn("법률·KNIA 근거", plan["user_message"])
        self.assertTrue(plan["recovery_suggestions"])

    def test_reference_only_result_explains_recovery_path(self):
        result = build_reflection_loop_result(
            initial_plan={
                "requery_reasons": ["family:legal"],
                "query_terms": ["도로교통법 안전거리"],
            },
            final_evidence_audit={
                "scenario_evidence_coverage": {
                    "missing_requirements": ["family:legal", "average_score"],
                    "decision_ready": False,
                }
            },
            input_requirements={"blocking_fields": []},
            followup_loop={"remaining_question_count": 0},
            judgment_contract={
                "overall_status": "needs_review",
                "presentation_policy": {"finality": "reference_only"},
                "must_not_present_as_final": True,
            },
            requery_attempted=True,
            requery_added_count=1,
        )

        self.assertEqual(result["status"], "reference_only")
        self.assertEqual(result["next_action"], "present_reference_only")
        self.assertIn("추가 근거 1개", result["user_message"])
        self.assertIn("도로교통법 안전거리", result["initial_query_terms"])
        self.assertTrue(any("법률 근거" in item for item in result["recovery_suggestions"]))


if __name__ == "__main__":
    unittest.main()
