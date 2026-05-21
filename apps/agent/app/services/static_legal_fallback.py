from __future__ import annotations

from typing import Any


_STATIC_CHUNKS: list[dict[str, Any]] = [
    {
        "chunk_id": "static:rt-law:safe-distance",
        "title": "도로교통법 안전거리 유지 의무",
        "source": "교통사고 법률 설명 자료",
        "law_name": "도로교통법",
        "article_title": "앞차와의 안전거리 및 전방주시 의무",
        "snippet": "뒤차는 앞차와 안전거리를 유지하고 전방 상황에 맞춰 속도를 줄일 주의의무가 있습니다.",
        "plain_summary": "후미추돌 사고에서는 뒤차가 안전거리를 지켰는지와 전방주시를 했는지가 핵심입니다.",
        "related_reason": "정차 또는 감속 중 뒤에서 추돌된 사고와 직접 관련된 확인 기준입니다.",
        "keywords": ["후미", "뒤차", "추돌", "안전거리", "정차", "급정거", "rear", "distance"],
        "score": 0.39,
    },
    {
        "chunk_id": "static:rt-law:signal",
        "title": "도로교통법 신호 준수 의무",
        "source": "교통사고 법률 설명 자료",
        "law_name": "도로교통법",
        "article_title": "교차로 신호 및 우선권 확인",
        "snippet": "교차로 사고에서는 각 차량의 신호 상태, 진입 시점, 우선권이 중요한 판단 요소입니다.",
        "plain_summary": "신호위반이나 선진입 여부가 다투어지는 사고에서 확인해야 하는 기준입니다.",
        "related_reason": "교차로 또는 신호위반 입력이 있을 때 참고할 수 있는 기준입니다.",
        "keywords": ["교차로", "신호", "좌회전", "우회전", "직진", "우선권", "intersection", "signal"],
        "score": 0.38,
    },
    {
        "chunk_id": "static:rt-law:lane-change",
        "title": "도로교통법 차로변경 주의의무",
        "source": "교통사고 법률 설명 자료",
        "law_name": "도로교통법",
        "article_title": "진로변경 시 주변 차량 확인 의무",
        "snippet": "차로를 바꾸는 차량은 방향지시등 사용, 사각지대 확인, 충분한 거리 확보가 필요합니다.",
        "plain_summary": "차선변경 중 사고에서는 변경 차량이 주변 차량을 충분히 확인했는지가 핵심입니다.",
        "related_reason": "차선변경, 끼어들기, 측면 충돌 입력과 관련된 기준입니다.",
        "keywords": ["차선", "차로", "진로", "변경", "끼어들", "방향지시등", "사각지대", "lane", "merge"],
        "score": 0.38,
    },
    {
        "chunk_id": "static:special-act:criminal",
        "title": "교통사고처리 특례법 형사책임 확인",
        "source": "교통사고 법률 설명 자료",
        "law_name": "교통사고처리 특례법",
        "article_title": "중과실 및 인명피해 확인",
        "snippet": "인명피해, 12대 중과실, 도주 여부가 있으면 형사책임 검토가 필요합니다.",
        "plain_summary": "다친 사람이 있거나 중대한 법규 위반이 의심되면 신고와 형사책임 여부를 확인해야 합니다.",
        "related_reason": "부상, 음주, 무면허, 신호위반, 뺑소니 입력과 관련된 기준입니다.",
        "keywords": ["형사", "신고", "중과실", "부상", "인명피해", "음주", "무면허", "뺑소니", "criminal"],
        "score": 0.41,
    },
    {
        "chunk_id": "static:criminal-law:injury",
        "title": "형법상 과실치상 검토 기준",
        "source": "교통사고 법률 설명 자료",
        "law_name": "형법",
        "article_title": "업무상 과실과 상해 발생 여부",
        "snippet": "사고로 사람이 다친 경우 주의의무 위반, 예견 가능성, 인과관계를 확인해야 합니다.",
        "plain_summary": "부상자가 있는 사고에서는 치료 기록과 사고 경위를 함께 확인해야 합니다.",
        "related_reason": "대인 접수나 진단서가 필요한 사고와 관련된 기준입니다.",
        "keywords": ["부상", "상해", "진단서", "대인", "치료", "injury"],
        "score": 0.37,
    },
    {
        "chunk_id": "static:fault-guide:rear-end",
        "title": "후미추돌 과실비율 참고 기준",
        "source": "교통사고 법률 설명 자료",
        "law_name": "과실비율 인정기준",
        "article_title": "정차 또는 감속 차량을 뒤에서 추돌한 사고",
        "snippet": "정차 또는 정상 감속 중인 앞차를 뒤차가 추돌했다면 일반적으로 뒤차 책임이 크게 검토됩니다.",
        "plain_summary": "피추돌 차량이 정상적으로 정차 중이었다면 뒤차의 안전거리 미확보가 중요한 판단 요소입니다.",
        "related_reason": "정차 중 뒤에서 추돌당한 사고와 직접 관련된 과실비율 참고 기준입니다.",
        "keywords": ["후미", "뒤차", "추돌", "정차", "안전거리", "피추돌", "rear", "stopped"],
        "score": 0.43,
    },
    {
        "chunk_id": "static:fault-guide:intersection",
        "title": "교차로 사고 과실비율 참고 기준",
        "source": "교통사고 법률 설명 자료",
        "law_name": "과실비율 인정기준",
        "article_title": "교차로 신호와 진입 순서",
        "snippet": "교차로 사고는 신호 준수 여부, 선진입, 시야 확보, 속도 등을 함께 봅니다.",
        "plain_summary": "교차로에서 충돌한 사고라면 신호와 진입 순서가 과실 판단의 핵심입니다.",
        "related_reason": "교차로 또는 신호위반 사고와 관련된 과실비율 참고 기준입니다.",
        "keywords": ["교차로", "신호", "선진입", "속도", "우선권", "intersection"],
        "score": 0.42,
    },
    {
        "chunk_id": "static:insurance:process",
        "title": "보험 처리 기본 체크리스트",
        "source": "교통사고 법률 설명 자료",
        "law_name": "보험 처리 안내",
        "article_title": "접수번호, 영상, 사진, 진단서 보관",
        "snippet": "보험 접수번호, 블랙박스 원본, 현장 사진, 수리 견적서, 진료 기록을 확보해야 합니다.",
        "plain_summary": "사고 직후에는 증거 보관과 보험 접수 진행 상황을 기록해 두는 것이 중요합니다.",
        "related_reason": "모든 교통사고에서 보험 접수와 증거 보관에 참고할 수 있는 기준입니다.",
        "keywords": ["보험", "접수", "블랙박스", "사진", "견적", "진단서", "insurance", "claim"],
        "score": 0.36,
    },
]


def retrieve_static_legal_chunks(query: str, limit: int = 5) -> list[dict[str, Any]]:
    q = (query or "").lower()
    ranked: list[tuple[int, float, dict[str, Any]]] = []
    for item in _STATIC_CHUNKS:
        keyword_hits = sum(1 for k in item["keywords"] if str(k).lower() in q)
        score = float(item["score"]) + keyword_hits * 0.04
        payload = {k: v for k, v in item.items() if k != "keywords"} | {"score": round(score, 3)}
        ranked.append((keyword_hits, score, payload))
    max_hits = max((hits for hits, _, _ in ranked), default=0)
    if max_hits > 0:
        ranked = [item for item in ranked if item[0] > 0]
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [x[2] for x in ranked[: max(1, limit)]]
