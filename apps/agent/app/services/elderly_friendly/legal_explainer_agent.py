from __future__ import annotations

from typing import Any
from app.services.elderly_friendly.ui_text_mapper import evidence_confidence_label, scrub_user_text

_USELESS_SNIPPETS = {"형사", "타법개정", "일부개정", "전부개정", "법령", "판례", "부칙", "개정문"}

class LegalExplainerAgent:
    def explain(self, evidence: list[dict[str, Any]], result: dict[str, Any]) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        scenario = result.get("scenario_type") or ""
        for item in sorted(evidence, key=lambda x: (int(x.get("display_priority") or 100), -float(x.get("score") or 0))):
            card = self.simplify_evidence_item(item, scenario)
            signature = (card["law_name"], card["easy_title"])
            if any((x["law_name"], x["easy_title"]) == signature for x in cards):
                continue
            cards.append(card)
            if len(cards) >= 6:
                break
        return cards or [self._fallback_card(scenario)]

    def simplify_evidence_item(self, item: dict[str, Any], scenario: str) -> dict[str, str]:
        tags = " ".join(item.get("scenario_tags") or [])
        keywords = " ".join(item.get("keywords") or [])
        easy_title = self._short_title(item.get("article_title") or item.get("chunk_summary") or item.get("title") or "교통사고 관련 확인 사항")
        law_name = self._short_law_name(item.get("law_name") or self._infer_law_name(item))
        plain = item.get("plain_summary") or item.get("snippet") or ""
        if self.is_useless_snippet(plain):
            plain = self._default_plain_summary(scenario, tags, keywords, easy_title)
        related = item.get("related_reason") or self.make_related_reason(item, scenario)
        source = item.get("source") or item.get("source_label") or "국가법령정보센터 또는 과실비율 인정기준 자료"
        return {
            "law_name": scrub_user_text(law_name, "교통사고 관련 기준"),
            "easy_title": scrub_user_text(easy_title, "교통사고 관련 확인 사항"),
            "easy_explanation": scrub_user_text(plain, "이 사고에서 확인해야 할 법률상 기준입니다."),
            "related_to_this_case": scrub_user_text(related, "입력하신 사고 사실과 연결해서 참고할 수 있는 근거입니다."),
            "confidence_label": "관련성이 있는 근거입니다." if evidence_confidence_label(item.get("score")) != "낮음" else "참고용 근거입니다.",
            "source_label": self._short_source_label(source),
        }

    def is_useless_snippet(self, snippet: Any) -> bool:
        value = str(snippet or "").strip()
        if len(value) < 20:
            return True
        return value in _USELESS_SNIPPETS or any(token == value for token in _USELESS_SNIPPETS)

    def make_related_reason(self, item: dict[str, Any], scenario: str) -> str:
        tags = " ".join(item.get("scenario_tags") or [])
        keywords = " ".join(item.get("keywords") or [])
        return self._default_related_reason(scenario, tags, keywords)

    def _infer_law_name(self, item: dict[str, Any]) -> str:
        text = " ".join(str(x or "") for x in [item.get("title"), item.get("snippet"), item.get("chunk_summary"), item.get("source")])
        if "보험" in text:
            return "보험 처리 기준"
        if "특정범죄" in text or "어린이" in text or "민식" in text:
            return "어린이보호구역 사고 기준"
        if "교통사고처리" in text or "12대" in text:
            return "중대한 교통법규 위반 기준"
        return "도로교통법"

    def _short_title(self, title: Any) -> str:
        text = scrub_user_text(title, "교통사고 관련 확인 사항")
        mapping = {
            "도로교통법위반": "교통법규 위반 여부",
            "안전거리": "안전거리 유지 의무",
            "사고 후": "사고 후 조치 의무",
            "보행자": "보행자 보호 의무",
            "어린이": "어린이보호구역 주의 의무",
            "신호": "신호 준수 의무",
            "차선": "차선변경 주의 의무",
            "보험": "보험 처리 절차",
        }
        for key, value in mapping.items():
            if key in text:
                return value
        if len(text) > 26:
            return text[:24].rstrip() + "…"
        return text

    def _short_law_name(self, name: Any) -> str:
        text = scrub_user_text(name, "교통사고 관련 기준")
        if "특정범죄" in text or "민식" in text or "어린이" in text:
            return "어린이보호구역 사고 기준"
        if "교통사고처리" in text or "12대" in text:
            return "교통사고처리 특례법"
        if "보험" in text:
            return "보험 처리 기준"
        if "도로교통" in text:
            return "도로교통법"
        if len(text) > 18:
            return text[:16].rstrip() + "…"
        return text

    def _short_source_label(self, source: Any) -> str:
        text = scrub_user_text(source, "국가법령정보센터 또는 과실비율 인정기준 자료")
        if "local" in text.lower() or "내부" in text:
            return "교통사고 법률 설명 자료"
        if len(text) > 24:
            return "국가법령정보센터 또는 과실비율 인정기준 자료"
        return text

    def _default_plain_summary(self, scenario: str, tags: str, keywords: str, title: str) -> str:
        joined = " ".join([scenario, tags, keywords, title])
        if "rear" in joined or "safe_distance" in joined or "후미" in joined or "안전거리" in joined:
            return "뒤차는 앞차가 멈출 경우를 대비해 충분한 거리를 두고 운전해야 합니다."
        if "school" in joined or "child" in joined or "어린이" in joined or "민식" in joined:
            return "어린이보호구역에서는 어린이를 보호하기 위해 운전자가 더 조심해야 합니다."
        if "crosswalk" in joined or "pedestrian" in joined or "보행자" in joined:
            return "횡단보도나 보행자가 있는 상황에서는 보행자 보호가 우선입니다."
        if "signal" in joined or "신호" in joined:
            return "교차로에서는 신호를 지켰는지가 사고 책임 판단에 중요합니다."
        if "lane" in joined or "차선" in joined:
            return "차선을 바꿀 때는 주변 차량을 충분히 살피고 안전하게 진입해야 합니다."
        if "report" in joined or "신고" in joined or "조치" in joined:
            return "사고가 나면 정차하고 다친 사람이 있는지 확인하며 필요한 조치를 해야 합니다."
        return "교통사고 책임과 대응 방법을 판단할 때 참고할 수 있는 기준입니다."

    def _default_related_reason(self, scenario: str, tags: str, keywords: str) -> str:
        joined = " ".join([scenario, tags, keywords])
        if "rear" in joined or "safe_distance" in joined:
            return "이번 사고는 정차 중 뒤차가 추돌한 상황이므로, 뒤차가 안전거리를 지켰는지가 중요한 판단 요소입니다."
        if "school" in joined or "child" in joined:
            return "어린이보호구역 또는 어린이 피해가 관련되면 신고와 형사책임 검토가 더 중요해집니다."
        if "signal" in joined:
            return "상대 차량이 신호를 위반했는지에 따라 책임 판단이 달라질 수 있습니다."
        if "lane" in joined:
            return "차선을 바꾼 차량이 주변을 살피고 방향지시등을 켰는지 확인해야 합니다."
        if "pedestrian" in joined or "crosswalk" in joined:
            return "보행자가 있었거나 횡단보도 근처라면 보행자 보호 의무가 중요합니다."
        return "입력하신 사고 사실과 연결해서 참고할 수 있는 근거입니다."

    def _fallback_card(self, scenario: str) -> dict[str, str]:
        return {
            "law_name": "도로교통법",
            "easy_title": "교통사고 기본 주의의무",
            "easy_explanation": self._default_plain_summary(scenario, "", "", ""),
            "related_to_this_case": self._default_related_reason(scenario, "", ""),
            "confidence_label": "참고용 근거입니다.",
            "source_label": "교통사고 법률 설명 자료",
        }
