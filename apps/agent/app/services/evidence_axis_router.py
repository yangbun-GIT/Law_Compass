from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.services.party_agents.base import canonical_party


VERSION = "evidence-axis-router-v1"

PARTY_BY_CHART_PREFIX = {
    "\ucc28": "car_vs_car",
    "\ubcf4": "car_vs_person",
    "\uc790": "car_vs_bicycle",
    "\uac70": "car_vs_bicycle",
    "\uae30": "car_vs_object",
    "\ub2e8": "single_vehicle",
}

PEDESTRIAN_TERMS = (
    "pedestrian",
    "crosswalk",
    "school_zone",
    "child",
    "\ubcf4\ud589\uc790",
    "\ud6a1\ub2e8\ubcf4\ub3c4",
    "\uc5b4\ub9b0\uc774\ubcf4\ud638\uad6c\uc5ed",
)
BICYCLE_TERMS = ("bicycle", "cyclist", "\uc790\uc804\uac70")
MOTORCYCLE_TERMS = ("motorcycle", "motorbike", "two_wheeler", "\uc774\ub95c\ucc28", "\uc624\ud1a0\ubc14\uc774")
OBJECT_TERMS = ("fixed_object", "road_object", "guardrail", "facility", "\uc2dc\uc124\ubb3c", "\uae30\ubb3c")
VEHICLE_CONTEXT_TERMS = ("vehicle", "car_vs_car", "rear_end", "intersection", "centerline", "lane_change")


def route_evidence_by_accident_axis(
    items: Iterable[dict[str, Any]],
    *,
    facts: dict[str, Any] | None,
    accident_party_type: str | None,
    scenario_type: str | None,
) -> dict[str, Any]:
    primary: list[dict[str, Any]] = []
    secondary: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for item in items or []:
        if not isinstance(item, dict):
            continue
        routed = classify_evidence_axis(
            item,
            facts=facts or {},
            accident_party_type=accident_party_type,
            scenario_type=scenario_type,
        )
        payload = {**item, "evidence_axis": routed}
        status = routed["status"]
        if status == "excluded":
            excluded.append(payload)
        elif status == "secondary":
            secondary.append(payload)
        else:
            primary.append(payload)

    return {
        "version": VERSION,
        "primary": primary,
        "secondary": secondary,
        "excluded": excluded,
        "summary": {
            "primary_count": len(primary),
            "secondary_count": len(secondary),
            "excluded_count": len(excluded),
            "excluded_reasons": _count_reasons(excluded),
            "secondary_reasons": _count_reasons(secondary),
        },
    }


def classify_evidence_axis(
    item: dict[str, Any],
    *,
    facts: dict[str, Any],
    accident_party_type: str | None,
    scenario_type: str | None,
) -> dict[str, Any]:
    expected_party = canonical_party(accident_party_type)
    item_party = _item_party(item)
    text = _item_text(item)
    tags = _item_tags(item)
    environment_axes = _environment_axes(text, tags)

    if expected_party == "unknown":
        return _result("primary", expected_party, item_party, "unknown_accident_axis_allows_reference", environment_axes)

    if item_party != "unknown" and item_party != expected_party:
        return _result("excluded", expected_party, item_party, "party_axis_mismatch", environment_axes)

    inferred_party = _infer_party_from_text(text, tags)
    if inferred_party != "unknown" and inferred_party != expected_party:
        if expected_party == "car_vs_car" and inferred_party in {"car_vs_person", "car_vs_bicycle", "car_vs_motorcycle"}:
            return _result("secondary", expected_party, inferred_party, "environment_axis_not_direct_collision_axis", environment_axes)
        return _result("excluded", expected_party, inferred_party, "inferred_party_axis_mismatch", environment_axes)

    if expected_party == "car_vs_car" and environment_axes and not _direct_non_vehicle_partner(facts):
        if _has_vehicle_axis(text, tags, scenario_type):
            return _result("secondary", expected_party, item_party, "vehicle_case_environment_axis", environment_axes)
        if environment_axes.intersection({"pedestrian", "bicycle", "motorcycle"}):
            return _result("secondary", expected_party, item_party, "environment_axis_not_direct_collision_axis", environment_axes)

    return _result("primary", expected_party, item_party, "accident_axis_match", environment_axes)


def _item_party(item: dict[str, Any]) -> str:
    for key in ("major_party_type", "accident_party_type", "party_type"):
        party = canonical_party(item.get(key))
        if party != "unknown":
            return party
    chart = str(item.get("aggregate_chart_no") or item.get("chart_no") or "").strip()
    for prefix, party in PARTY_BY_CHART_PREFIX.items():
        if chart.startswith(prefix):
            return party
    return "unknown"


def _infer_party_from_text(text: str, tags: set[str]) -> str:
    if _contains_any(text, PEDESTRIAN_TERMS) or tags.intersection({"pedestrian", "school_zone"}):
        if not _has_any_vehicle_context(text, tags):
            return "car_vs_person"
    if _contains_any(text, BICYCLE_TERMS) or "bicycle" in tags:
        if not _has_any_vehicle_context(text, tags):
            return "car_vs_bicycle"
    if _contains_any(text, MOTORCYCLE_TERMS) or "motorcycle" in tags:
        if not _has_any_vehicle_context(text, tags):
            return "car_vs_motorcycle"
    if _contains_any(text, OBJECT_TERMS) or "object" in tags:
        return "car_vs_object"
    return "unknown"


def _environment_axes(text: str, tags: set[str]) -> set[str]:
    axes: set[str] = set()
    if _contains_any(text, PEDESTRIAN_TERMS) or tags.intersection({"pedestrian", "crosswalk", "school_zone", "child"}):
        axes.add("pedestrian")
    if _contains_any(text, BICYCLE_TERMS) or "bicycle" in tags:
        axes.add("bicycle")
    if _contains_any(text, MOTORCYCLE_TERMS) or "motorcycle" in tags:
        axes.add("motorcycle")
    if _contains_any(text, OBJECT_TERMS) or "object" in tags:
        axes.add("object")
    if "signal" in text or "intersection" in text or tags.intersection({"signal_violation", "intersection"}):
        axes.add("signal_or_intersection")
    if "centerline" in text or "oncoming" in text or tags.intersection({"centerline", "oncoming_vehicle"}):
        axes.add("centerline_or_oncoming")
    return axes


def _direct_non_vehicle_partner(facts: dict[str, Any]) -> bool:
    for field in ("direct_collision_partner_type", "collision_partner_type", "primary_collision_target"):
        value = str(facts.get(field) or "").strip().lower()
        if value in {"pedestrian", "person", "bicycle", "cyclist", "motorcycle", "motorbike", "object"}:
            return True
    return False


def _has_vehicle_axis(text: str, tags: set[str], scenario_type: str | None) -> bool:
    if canonical_party(scenario_type) == "car_vs_car":
        return True
    scenario = str(scenario_type or "").lower()
    if scenario in {"rear_end_collision", "intersection_collision", "intersection_signal_violation", "lane_change_collision", "centerline_obstacle_collision"}:
        return True
    return _has_any_vehicle_context(text, tags)


def _has_any_vehicle_context(text: str, tags: set[str]) -> bool:
    return _contains_any(text, VEHICLE_CONTEXT_TERMS) or bool(tags.intersection(VEHICLE_CONTEXT_TERMS))


def _item_text(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "chunk_id",
        "title",
        "article_title",
        "plain_summary",
        "related_reason",
        "accident_summary",
        "law_name",
        "source_type",
        "scenario_type",
    ):
        parts.append(str(item.get(key) or ""))
    for key in ("scenario_tags", "display_tags", "keywords"):
        value = item.get(key) or []
        if isinstance(value, (list, tuple, set)):
            parts.extend(str(x) for x in value)
        else:
            parts.append(str(value))
    return " ".join(parts).lower()


def _item_tags(item: dict[str, Any]) -> set[str]:
    tags: set[str] = set()
    for key in ("scenario_tags", "display_tags"):
        value = item.get(key) or []
        if isinstance(value, (list, tuple, set)):
            tags.update(str(x).strip().lower() for x in value if str(x).strip())
    return tags


def _contains_any(text: str, tokens: Iterable[str]) -> bool:
    hay = str(text or "").lower()
    return any(str(token).lower() in hay for token in tokens)


def _result(
    status: str,
    expected_party: str,
    item_party: str,
    reason: str,
    environment_axes: set[str],
) -> dict[str, Any]:
    return {
        "status": status,
        "expected_party_type": expected_party,
        "item_party_type": item_party,
        "reason": reason,
        "environment_axes": sorted(environment_axes),
        "version": VERSION,
    }


def _count_reasons(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        reason = str((item.get("evidence_axis") or {}).get("reason") or "unknown")
        counts[reason] = counts.get(reason, 0) + 1
    return counts
