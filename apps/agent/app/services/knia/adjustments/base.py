from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AdjustmentEvaluation:
    base_fault: dict[str, int] | None = None
    final_fault: dict[str, int] | None = None
    fault_range: dict[str, str] | None = None
    applied_adjustments: list[dict[str, Any]] = field(default_factory=list)
    not_applied_adjustments: list[dict[str, Any]] = field(default_factory=list)
    unknown_adjustments: list[dict[str, Any]] = field(default_factory=list)
    conditional_outcomes: list[dict[str, Any]] = field(default_factory=list)
    required_questions: list[dict[str, Any]] = field(default_factory=list)
    source_chart: dict[str, Any] | None = None
    confidence: float = 0.0
    policy: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def clamp(value: Any) -> int:
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 0


def pair(my: Any, other: Any | None = None) -> dict[str, int]:
    mine = clamp(my)
    theirs = clamp(100 - mine if other is None else other)
    return {"my": mine, "other": theirs}

