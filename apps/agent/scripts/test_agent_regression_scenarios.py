from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable

if os.getenv("LAWCOMPASS_REGRESSION_USE_LLM", "0") != "1":
    os.environ["OPENAI_API_KEY"] = ""

from app.services.accident_perspective import (  # noqa: E402
    BICYCLE,
    FRONT_VEHICLE,
    LANE_CHANGING_VEHICLE,
    SIGNAL_COMPLIANT_VEHICLE,
    STRAIGHT_VEHICLE,
)
from app.services.judgment_contract import (  # noqa: E402
    STATUS_NEEDS_REVIEW,
    STATUS_SUPPORTED,
)
from app.services.orchestrator import analyze_case, analyze_video_case  # noqa: E402


SUPPORTED_OR_REVIEW = {STATUS_SUPPORTED, STATUS_NEEDS_REVIEW}


@dataclass(frozen=True)
class RegressionScenario:
    name: str
    check: Callable[[dict[str, Any]], None]
    text: str = ""
    run: Callable[[], dict[str, Any]] | None = None


def main() -> None:
    failures: list[str] = []
    for scenario in _scenarios():
        try:
            result = scenario.run() if scenario.run else analyze_case(scenario.text)
            scenario.check(result)
            _print_result("PASS", scenario.name, result)
        except AssertionError as exc:
            failures.append(f"{scenario.name}: {exc}")
            try:
                _print_result("FAIL", scenario.name, locals().get("result", {}))
            except Exception:
                pass

    if failures:
        joined = "\n".join(f"- {failure}" for failure in failures)
        raise AssertionError(f"Agent regression scenarios failed:\n{joined}")


def _scenarios() -> list[RegressionScenario]:
    return [
        RegressionScenario(
            name="rear_end_victim",
            check=_check_rear_end_victim,
            text="\uc815\ucc28 \uc911 \ub4a4\uc5d0\uc11c \ucd94\ub3cc\ub2f9\ud588\uc2b5\ub2c8\ub2e4.",
        ),
        RegressionScenario(
            name="video_rear_end_overrides_conflicting_user_fact",
            check=_check_video_rear_end_conflict,
            run=_run_video_rear_end_conflict,
        ),
        RegressionScenario(
            name="opponent_lane_change",
            check=_check_opponent_lane_change,
            text="\uc0c1\ub300 \ucc28\ub7c9\uc774 \uac11\uc790\uae30 \ucc28\uc120\ubcc0\uacbd\ud558\uba70 \ub07c\uc5b4\ub4e4\uc5b4 \ucda9\ub3cc\ud588\uc2b5\ub2c8\ub2e4.",
        ),
        RegressionScenario(
            name="user_lane_change",
            check=_check_user_lane_change,
            text="\uc81c\uac00 \ucc28\uc120\ubcc0\uacbd\uc744 \ud558\ub2e4\uac00 \uc9c1\uc9c4 \ucc28\ub7c9\uacfc \ucda9\ub3cc\ud588\uc2b5\ub2c8\ub2e4.",
        ),
        RegressionScenario(
            name="opponent_signal_violation",
            check=_check_opponent_signal_violation,
            text="\uc0c1\ub300 \ucc28\ub7c9\uc774 \ube68\uac04\ubd88\uc5d0 \uc2e0\ud638\uc704\ubc18\uc744 \ud574\uc11c \uad50\ucc28\ub85c\uc5d0\uc11c \ucda9\ub3cc\ud588\uc2b5\ub2c8\ub2e4.",
        ),
        RegressionScenario(
            name="user_bicycle_collision",
            check=_check_user_bicycle_collision,
            text="\uc81c\uac00 \uc790\uc804\uac70\ub97c \ud0c0\uace0 \uac00\ub2e4\uac00 \ucc28\ub7c9\uacfc \ucda9\ub3cc\ud588\uc2b5\ub2c8\ub2e4.",
        ),
    ]


def _run_video_rear_end_conflict() -> dict[str, Any]:
    return analyze_video_case(
        preprocessed_summary="\uc81c\uac00 \uc55e\ucc28\ub97c \ucd94\ub3cc\ud588\uc2b5\ub2c8\ub2e4.",
        ai_profile="default_vehicle_collision",
        specialist_roles=[],
        video_metadata={
            "metadata": {
                "duration_sec": 6.0,
                "representative_frames": ["/frames/rear_end_1.jpg"],
                "observations": [
                    {
                        "field": "stopped",
                        "value": True,
                        "confidence": 0.92,
                        "source": "frame_analysis",
                        "frame_refs": ["rear_end_1.jpg"],
                        "reason": "Ego vehicle appears stationary before impact.",
                    },
                    {
                        "field": "impact_direction",
                        "value": "rear",
                        "confidence": 0.91,
                        "source": "frame_analysis",
                        "frame_refs": ["rear_end_1.jpg"],
                        "reason": "Impact is observed from behind.",
                    },
                ],
            }
        },
        structured_facts={"opponent_behavior": "front_collision"},
    )


def _check_rear_end_victim(result: dict[str, Any]) -> None:
    _assert_common_contract(result)
    fault = result.get("fault_ratio") or {}
    assert result.get("scenario_type") == "rear_end_collision", result.get("scenario_type")
    assert fault.get("user_vehicle_role") == FRONT_VEHICLE, fault
    assert fault.get("my") == 0, fault
    assert fault.get("other") == 100, fault
    _assert_knia_chart_when_db_available(result, "\ucc2841-1")


def _check_video_rear_end_conflict(result: dict[str, Any]) -> None:
    _assert_common_contract(result)
    fault = result.get("fault_ratio") or {}
    facts = result.get("structured_facts") or {}
    arbitration = result.get("fact_arbitration") or {}
    conflicts = arbitration.get("conflicts") or []
    source = (arbitration.get("fact_sources") or {}).get("opponent_behavior") or {}

    assert result.get("scenario_type") == "rear_end_collision", result.get("scenario_type")
    assert facts.get("stopped") is True, facts
    assert facts.get("opponent_behavior") == "rear_collision", facts
    assert source.get("source") == "video", source
    assert "opponent_behavior" in arbitration.get("applied_video_fields", []), arbitration
    assert "stopped" in arbitration.get("applied_video_fields", []), arbitration
    assert any(item.get("field") == "opponent_behavior" and item.get("winner") == "video" for item in conflicts), conflicts
    assert fault.get("user_vehicle_role") == FRONT_VEHICLE, fault
    assert fault.get("my") == 0, fault
    assert fault.get("other") == 100, fault


def _check_opponent_lane_change(result: dict[str, Any]) -> None:
    _assert_common_contract(result)
    fault = result.get("fault_ratio") or {}
    assert result.get("scenario_type") == "lane_change_collision", result.get("scenario_type")
    assert fault.get("user_vehicle_role") == STRAIGHT_VEHICLE, fault
    assert fault.get("my") == 30, fault
    assert fault.get("other") == 70, fault
    _assert_knia_chart_when_db_available(result, "\ucc2843-2")


def _check_user_lane_change(result: dict[str, Any]) -> None:
    _assert_common_contract(result)
    fault = result.get("fault_ratio") or {}
    assert result.get("scenario_type") == "lane_change_collision", result.get("scenario_type")
    assert fault.get("user_vehicle_role") == LANE_CHANGING_VEHICLE, fault
    assert fault.get("my") == 70, fault
    assert fault.get("other") == 30, fault
    _assert_knia_chart_when_db_available(result, "\ucc2843-2")


def _check_opponent_signal_violation(result: dict[str, Any]) -> None:
    _assert_common_contract(result)
    fault = result.get("fault_ratio") or {}
    primary_match = result.get("knia_primary_match")
    assert result.get("scenario_type") == "intersection_signal_violation", result.get("scenario_type")
    assert fault.get("user_vehicle_role") == SIGNAL_COMPLIANT_VEHICLE, fault
    assert fault.get("my") == 0, fault
    assert fault.get("other") == 100, fault
    assert primary_match is None or str(primary_match.get("chart_no") or "").startswith("\ucc2812"), primary_match
    if primary_match is None:
        assert fault.get("presentation_status") == "review_required", fault
        assert result.get("presentation_policy", {}).get("finality") == "reference_only", result.get("presentation_policy")


def _check_user_bicycle_collision(result: dict[str, Any]) -> None:
    _assert_common_contract(result)
    fault = result.get("fault_ratio") or {}
    primary_match = result.get("knia_primary_match")
    evidence_coverage = (result.get("evidence_audit") or {}).get("scenario_evidence_coverage") or {}
    assert result.get("scenario_type") == "bicycle_collision", result.get("scenario_type")
    assert fault.get("user_vehicle_role") == BICYCLE, fault
    assert primary_match is None or primary_match.get("accident_party_type") == "car_vs_bicycle", primary_match
    assert evidence_coverage.get("coverage_level") in {"medium", "high"}, evidence_coverage
    assert evidence_coverage.get("scenario_relevant_count", 0) >= 2, evidence_coverage


def _assert_common_contract(result: dict[str, Any]) -> None:
    judgment = result.get("agent_judgment") or {}
    evidence_coverage = (result.get("evidence_audit") or {}).get("scenario_evidence_coverage") or {}
    assert judgment.get("overall_status") in SUPPORTED_OR_REVIEW, judgment
    assert "stage_statuses" in judgment, judgment
    assert "claim_coverage" in judgment, judgment
    assert result.get("presentation_policy", {}).get("finality") in {"supported", "reference_only", "blocked_for_final"}, result.get("presentation_policy")
    assert evidence_coverage.get("coverage_level") in {"high", "medium", "low"}, evidence_coverage
    assert "scenario_relevant_count" in evidence_coverage, evidence_coverage
    assert "evidence_family_counts" in evidence_coverage, evidence_coverage


def _assert_knia_chart_when_db_available(result: dict[str, Any], expected_chart_no: str) -> None:
    primary_match = result.get("knia_primary_match")
    if os.getenv("DATABASE_URL", "").strip():
        assert (primary_match or {}).get("chart_no") == expected_chart_no, primary_match
        return
    assert primary_match is None or (primary_match or {}).get("chart_no") == expected_chart_no, primary_match


def _print_result(status: str, name: str, result: dict[str, Any]) -> None:
    fault = result.get("fault_ratio") or {}
    judgment = result.get("agent_judgment") or {}
    coverage = ((result.get("evidence_audit") or {}).get("scenario_evidence_coverage") or {}).get("coverage_level")
    primary_match = result.get("knia_primary_match") or {}
    print(
        " ".join(
            [
                status,
                name,
                f"scenario={result.get('scenario_type')}",
                f"fault={fault.get('my')}:{fault.get('other')}",
                f"role={fault.get('user_vehicle_role')}",
                f"knia={primary_match.get('chart_no')}",
                f"judgment={judgment.get('overall_status')}",
                f"evidence_coverage={coverage}",
            ]
        )
    )


if __name__ == "__main__":
    main()
