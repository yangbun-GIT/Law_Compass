from pathlib import Path
from typing import Any


def select_openai_frames(frame_details: list[dict[str, Any]], max_frames: int) -> list[dict[str, Any]]:
    frames = [frame for frame in frame_details if frame.get("path") and Path(frame["path"]).exists()]
    if len(frames) <= max_frames:
        return frames
    if max_frames == 1:
        return [frames[len(frames) // 2]]
    object_first = _object_first_frame_indexes(frames, max_frames)
    if object_first:
        return [frames[index] for index in object_first]
    return [frames[index] for index in _event_focused_frame_indexes(len(frames), max_frames)]


def frame_selection_metadata(
    frame_details: list[dict[str, Any]],
    selected_frames: list[dict[str, Any]],
    *,
    strategy: str,
    max_frames: int,
) -> dict[str, Any]:
    available_frame_count = len([frame for frame in frame_details if frame.get("path") and Path(frame["path"]).exists()])
    return {
        "frame_selection_strategy": strategy,
        "available_frame_count": available_frame_count,
        "selected_frame_count": len(selected_frames),
        "frame_selection_max_frames": max_frames,
    }


def _object_first_frame_indexes(frames: list[dict[str, Any]], max_frames: int) -> list[int]:
    event_indexes = [
        index for index, frame in enumerate(frames)
        if frame.get("role") in {"accident_candidate", "event_context"}
    ]
    if not event_indexes:
        return []
    selected: list[int] = []

    def add(index: int) -> None:
        if len(selected) >= max_frames:
            return
        clamped = max(0, min(len(frames) - 1, index))
        if clamped not in selected:
            selected.append(clamped)

    add(0)
    add(len(frames) - 1)
    event_budget = max(1, max_frames - len(selected))
    distributed_events = _spread_indexes(event_indexes, min(len(event_indexes), event_budget))
    for index in distributed_events:
        add(index)
    for offset in (-1, 1, -2, 2):
        for index in distributed_events:
            add(index + offset)
            if len(selected) >= max_frames:
                return sorted(selected)
    for index in _event_focused_frame_indexes(len(frames), max_frames):
        add(index)
        if len(selected) >= max_frames:
            break
    return sorted(selected)


def _spread_indexes(indexes: list[int], count: int) -> list[int]:
    if count <= 0:
        return []
    values = sorted(dict.fromkeys(indexes))
    if count >= len(values):
        return values
    if count == 1:
        return [values[len(values) // 2]]
    selected: list[int] = []
    for step in range(count):
        pos = round(step * (len(values) - 1) / (count - 1))
        value = values[pos]
        if value not in selected:
            selected.append(value)
    return selected


def _event_focused_frame_indexes(frame_count: int, max_frames: int) -> list[int]:
    if frame_count <= max_frames:
        return list(range(frame_count))
    if max_frames <= 1:
        return [frame_count // 2]

    midpoint = frame_count // 2
    anchors = [
        0,
        frame_count - 1,
        midpoint,
        midpoint - 1,
        midpoint + 1,
        round((frame_count - 1) * 0.35),
        round((frame_count - 1) * 0.65),
    ]
    selected: list[int] = []
    for index in anchors:
        clamped = max(0, min(frame_count - 1, index))
        if clamped not in selected:
            selected.append(clamped)
        if len(selected) >= max_frames:
            return sorted(selected)

    for step in range(max_frames):
        index = round(step * (frame_count - 1) / (max_frames - 1))
        if index not in selected:
            selected.append(index)
        if len(selected) >= max_frames:
            break
    return sorted(selected)
