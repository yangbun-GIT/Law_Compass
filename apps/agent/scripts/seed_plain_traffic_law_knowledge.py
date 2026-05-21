from __future__ import annotations

import os
from dataclasses import dataclass
import psycopg
from psycopg.types.json import Jsonb
from app.services.legal.legal_vectorizer import vectorize_text

DB_URL = os.getenv("DATABASE_URL", "postgresql://law:lawpass@postgres:5432/lawcompass")
SOURCE_URI = "local://plain-traffic-law-knowledge-v1"

@dataclass(frozen=True)
class Seed:
    title: str
    law: str
    article: str
    text: str
    summary: str
    reason: str
    tags: list[str]
    keywords: list[str]
    priority: int

SEEDS = [
    Seed("안전거리 유지 의무", "도로교통법", "안전거리 유지 의무", "운전자는 앞차가 갑자기 정지하더라도 충돌을 피할 수 있는 필요한 거리를 확보해야 합니다.", "운전자는 앞차가 갑자기 멈추더라도 안전하게 멈출 수 있도록 충분한 거리를 두고 운전해야 합니다.", "뒤차가 사용자의 차량을 추돌했다면, 뒤차가 앞차와 안전거리를 지켰는지가 중요한 판단 요소입니다.", ["rear_end", "safe_distance", "fault_ratio"], ["후미추돌", "안전거리", "정차", "뒤차", "과실비율"], 10),
    Seed("사고 후 조치 의무", "도로교통법", "사고 후 정차 및 구호 조치", "교통사고가 발생하면 운전자는 즉시 정차하고 사상자를 구호하며 필요한 조치를 해야 합니다.", "교통사고가 나면 즉시 멈추고, 다친 사람이 있는지 확인하며, 필요한 조치를 해야 합니다.", "사고 뒤 상대방이 현장을 떠났거나 다친 사람이 있다면 신고와 사고 후 조치 여부가 중요합니다.", ["reporting", "hit_and_run", "injury"], ["사고 후 조치", "신고", "구호", "뺑소니", "인명피해"], 20),
    Seed("보행자 보호 의무", "도로교통법", "횡단보도와 보행자 보호", "횡단보도나 보행자가 통행하는 곳에서는 운전자가 속도를 줄이고 보행자를 보호해야 합니다.", "횡단보도나 보행자가 있는 상황에서는 운전자가 보행자 보호를 우선해야 합니다.", "보행자가 있었거나 횡단보도 근처에서 사고가 났다면 운전자의 보행자 보호 의무가 핵심입니다.", ["pedestrian", "crosswalk", "injury"], ["보행자", "횡단보도", "보행자 보호", "인명피해"], 25),
    Seed("12대 중과실 확인 기준", "교통사고처리 특례법", "12대 중과실 사고", "신호위반, 중앙선 침범, 제한속도 위반, 횡단보도 보행자 보호의무 위반, 음주운전, 무면허운전 등은 형사책임 검토가 필요할 수 있습니다.", "신호위반, 중앙선 침범, 음주운전 같은 큰 위반이 있으면 형사책임을 확인해야 할 수 있습니다.", "사고에 중대한 위반이 포함되면 단순 보험 처리만으로 끝나지 않을 수 있습니다.", ["twelve_gross_negligence", "criminal_liability", "signal_violation"], ["12대 중과실", "신호위반", "중앙선 침범", "음주운전", "무면허"], 30),
    Seed("어린이보호구역 사고", "특정범죄 가중처벌 등에 관한 법률", "어린이보호구역 내 어린이 사고", "어린이보호구역에서 어린이를 다치게 한 사고는 운전자의 주의의무가 더 엄격하게 검토될 수 있습니다.", "어린이보호구역에서 어린이가 다친 사고는 일반 사고보다 더 엄격하게 검토될 수 있습니다.", "피해자가 어린이이고 어린이보호구역이라면 신고와 형사책임 검토가 중요합니다.", ["school_zone", "child_protection", "injury", "criminal_liability"], ["어린이보호구역", "민식이법", "어린이", "스쿨존", "형사책임"], 12),
    Seed("신호위반 사고", "도로교통법", "신호 준수 의무", "교차로에서 운전자는 신호등과 교통정리를 따라야 하며 신호위반은 책임 판단의 중요한 요소입니다.", "교차로에서는 신호를 지키는지 여부가 사고 책임 판단에 매우 중요합니다.", "상대 차량이 빨간불에 진입했다면 상대방의 신호위반 여부가 핵심입니다.", ["signal_violation", "intersection", "fault_ratio", "criminal_liability"], ["신호위반", "교차로", "빨간불", "적색 신호", "과실비율"], 15),
    Seed("차선변경 사고", "도로교통법", "진로변경 시 주의의무", "차선을 변경하는 운전자는 주변 차량의 정상적인 통행을 방해하지 않도록 충분히 살피고 안전하게 진입해야 합니다.", "차선을 바꿀 때는 주변 차량을 충분히 살피고 안전하게 들어와야 합니다.", "상대 차량이 방향지시등 없이 갑자기 차선을 바꿨다면 차선변경 주의의무가 중요합니다.", ["lane_change", "turn_signal", "side_collision", "fault_ratio"], ["차선변경", "방향지시등", "진로변경", "측면충돌", "사각지대"], 18),
    Seed("보험 처리 일반 절차", "보험 처리 일반 절차", "사고 접수와 필요 서류", "교통사고 후에는 보험사 사고 접수, 블랙박스 제출, 차량 수리 견적, 진단서 확보 순서로 진행되는 경우가 많습니다.", "보험 처리는 사고 접수, 블랙박스 제출, 수리 견적, 진단서 확보 순서로 진행되는 경우가 많습니다.", "보험 처리를 원활하게 하려면 영상과 사진, 견적서, 진료 기록을 미리 정리해 두는 것이 좋습니다.", ["insurance", "documents", "action_plan"], ["보험", "대인접수", "대물접수", "수리 견적", "진단서"], 35),
    Seed("후미추돌 사고 과실 판단 요소", "과실비율 참고 기준", "후미추돌 기본 판단 요소", "정차 또는 서행 중 뒤차가 앞차를 추돌한 사고는 뒤차의 안전거리 미확보와 전방주시 태만이 중요한 판단 요소가 됩니다.", "정차 중 뒤에서 들이받힌 사고는 보통 뒤차의 책임이 더 크게 검토됩니다.", "사용자가 정차 중이었다면 내 책임보다 뒤차 책임이 더 크게 볼 가능성이 있습니다.", ["rear_end", "fault_ratio", "safe_distance"], ["후미추돌", "정차", "급정거", "과실", "전방주시"], 11),
    Seed("블랙박스 증거 보관 방법", "사고 증빙 정리 기준", "영상 원본 보관", "블랙박스 영상은 원본 파일을 삭제하지 말고 별도 저장해야 하며 사고 전후 장면과 시간 정보가 중요합니다.", "블랙박스 원본 영상은 삭제하지 말고 따로 저장해 두는 것이 중요합니다.", "영상 원본은 사고 상황, 정차 여부, 신호 상태, 충돌 위치를 확인하는 데 도움이 됩니다.", ["evidence", "blackbox", "action_plan"], ["블랙박스", "영상 원본", "증거", "보관", "사고 전후"], 5),
]

def main() -> None:
    inserted_docs = 0
    inserted_chunks = 0
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO kb_sources(name, source_type, source_uri, provider, version_tag, metadata)
                VALUES(%s, 'plain_seed', %s, 'local', 'plain-v1', %s)
                RETURNING id
            """, ("쉬운 교통법률 설명 데이터", SOURCE_URI, Jsonb({"purpose": "elderly-friendly legal explanation"})))
            source_id = cur.fetchone()[0]
            for i, seed in enumerate(SEEDS):
                raw = f"{seed.title}\n{seed.text}\n쉬운 설명: {seed.summary}\n관련성: {seed.reason}"
                cur.execute("""
                    INSERT INTO kb_documents(source_id,title,doc_type,jurisdiction,raw_text,summary,metadata,tsv)
                    VALUES(%s,%s,'plain_law_seed','KR',%s,%s,%s,to_tsvector('simple', %s)) RETURNING id
                """, (source_id, seed.title, raw, seed.summary, Jsonb({"law_name": seed.law, "article_title": seed.article}), raw))
                doc_id = cur.fetchone()[0]
                inserted_docs += 1
                cur.execute("""
                    INSERT INTO kb_chunks(document_id,chunk_index,chunk_text,chunk_summary,scenario_tags,keywords,metadata,tsv,plain_summary,related_reason,display_priority,source_url,law_name,article_title)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,to_tsvector('simple', %s),%s,%s,%s,%s,%s,%s) RETURNING id
                """, (doc_id, i, seed.text, seed.title, seed.tags, seed.keywords, Jsonb({"seed": True}), f"{seed.title} {seed.text} {seed.summary} {seed.reason} {' '.join(seed.keywords)}", seed.summary, seed.reason, seed.priority, SOURCE_URI, seed.law, seed.article))
                chunk_id = cur.fetchone()[0]
                vector, model = vectorize_text(f"{seed.title} {seed.text} {seed.summary} {seed.reason}")
                cur.execute("""
                    INSERT INTO kb_embeddings(chunk_id, embedding, embedding_model)
                    VALUES(%s, %s::vector, %s)
                    ON CONFLICT(chunk_id) DO UPDATE SET embedding=EXCLUDED.embedding, embedding_model=EXCLUDED.embedding_model, created_at=now()
                """, (chunk_id, vector, model))
                inserted_chunks += 1
            conn.commit()
    print(f"plain_traffic_law_seed inserted_documents={inserted_docs} inserted_chunks={inserted_chunks}")

if __name__ == "__main__":
    main()
