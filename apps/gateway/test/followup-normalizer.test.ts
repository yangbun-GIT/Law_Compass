import { describe, expect, it } from "vitest";
import { normalizeFollowupAnswers } from "../src/lib/followup-normalizer.js";

describe("followup normalizer", () => {
  it("normalizes Korean followup answers into canonical facts", () => {
    const result = normalizeFollowupAnswers(
      {
        injury: "다친 사람 없음",
        stopped: "완전히 정차 중",
        opponent_signal: "적색",
        lane_change_actor: "상대 차량",
      },
      {}
    );

    expect(result.patch.injury).toBe(false);
    expect(result.patch.stopped).toBe(true);
    expect(result.patch.sudden_brake).toBe(false);
    expect(result.patch.opponent_signal).toBe("red");
    expect(result.patch.opponent_signal_violation).toBe(true);
    expect(result.patch.opponent_lane_change).toBe(true);
    expect(result.patch.my_lane_change).toBe(false);
    expect(result.patch._followup_iteration).toBe(1);
    expect(result.patch._followup_answered_fields).toEqual(["injury", "stopped", "opponent_signal", "lane_change_actor"]);
  });

  it("tracks unresolved answers without turning them into false facts", () => {
    const result = normalizeFollowupAnswers(
      {
        injury: "확인 중",
        turn_signal: "영상으로 확인 필요",
      },
      { _followup_iteration: 1, _followup_answered_fields: ["stopped"] }
    );

    expect(result.patch.injury).toBeUndefined();
    expect(result.patch.turn_signal).toBeUndefined();
    expect(result.patch._followup_iteration).toBe(2);
    expect(result.patch._followup_answered_fields).toEqual(["stopped"]);
    expect(result.patch._followup_unresolved_fields).toEqual(["injury", "turn_signal"]);
  });

  it("normalizes video quality followup answers into canonical facts", () => {
    const result = normalizeFollowupAnswers(
      {
        opponent_behavior: "뒤에서 추돌",
        opponent_signal_violation: "예",
      },
      {}
    );

    expect(result.patch.opponent_behavior).toBe("rear_collision");
    expect(result.patch.opponent_signal_violation).toBe(true);
    expect(result.patch._followup_answered_fields).toEqual(["opponent_behavior", "opponent_signal_violation"]);
  });

  it("accepts canonical conflict-resolution values from diagnostics and E2E checks", () => {
    const result = normalizeFollowupAnswers(
      {
        stopped: false,
        opponent_behavior: "rear_collision",
        lane_change_actor: "opponent",
        opponent_signal: "red",
        opponent_signal_violation: true,
        injury: false,
      },
      {}
    );

    expect(result.patch.stopped).toBe(false);
    expect(result.patch.opponent_behavior).toBe("rear_collision");
    expect(result.patch.lane_change_actor).toBe("opponent");
    expect(result.patch.opponent_lane_change).toBe(true);
    expect(result.patch.my_lane_change).toBe(false);
    expect(result.patch.opponent_signal).toBe("red");
    expect(result.patch.opponent_signal_violation).toBe(true);
    expect(result.patch.injury).toBe(false);
    expect(result.patch._followup_answered_fields).toEqual([
      "stopped",
      "opponent_behavior",
      "lane_change_actor",
      "opponent_signal",
      "injury",
    ]);
  });
});
