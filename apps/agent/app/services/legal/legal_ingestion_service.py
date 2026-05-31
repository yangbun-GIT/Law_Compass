from __future__ import annotations

import os
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.services.legal.legal_chunker import chunk_legal_document
from app.services.legal.legal_normalizer import (
    NormalizedLegalDocument,
    normalize_law_api_item,
    normalize_law_detail_article,
    normalize_seed_document,
)
from app.services.legal.legal_vectorizer import vectorize_text
from app.services.legal_api_clients import fetch_law_search, fetch_road_traffic_law_articles

DB_URL = os.getenv("DATABASE_URL", "")

TRAFFIC_LAW_QUERIES = [
    "도로교통법",
    "교통사고처리 특례법",
    "특정범죄 가중처벌 등에 관한 법률 어린이보호구역",
    "어린이보호구역",
    "민식이법",
    "12대 중과실",
    "사고 후 조치",
    "신호위반",
    "중앙선 침범",
    "보행자 보호의무",
    "횡단보도",
    "음주운전",
    "무면허운전",
    "뺑소니",
    "자전거 교통사고",
]

LOCAL_SEED_DOCUMENTS: list[dict[str, Any]] = [
    {
        "title": "도로교통법 안전거리 및 안전운전 의무",
        "doc_type": "law_seed",
        "summary": "후미추돌, 안전거리, 전방주시 의무의 기본 근거",
        "raw_text": "도로교통법상 운전자는 앞차가 갑자기 정지하는 경우에도 충돌을 피할 수 있도록 필요한 거리를 확보하고 도로 상황에 맞게 안전하게 운전해야 한다. 후미추돌 사고에서는 후방 차량의 안전거리 확보, 전방주시, 제동 가능성이 주요 쟁점이 된다.",
        "keywords": ["후미추돌", "안전거리", "전방주시", "안전운전"],
        "scenario_tags": ["rear_end", "safe_distance", "safe_driving"],
    },
    {
        "title": "교통사고처리 특례법 12대 중과실 개요",
        "doc_type": "law_seed",
        "summary": "신호위반, 중앙선 침범, 횡단보도 보행자 보호의무 위반 등 중대한 과실 검토",
        "raw_text": "교통사고처리 특례법상 신호위반, 중앙선 침범, 제한속도 중대한 초과, 횡단보도 보행자 보호의무 위반, 음주운전, 무면허운전 등은 12대 중과실로 검토될 수 있다. 부상이나 사망이 있는 경우 형사책임 가능성을 별도로 확인해야 한다.",
        "keywords": ["12대 중과실", "신호위반", "중앙선 침범", "횡단보도", "음주운전", "무면허운전"],
        "scenario_tags": ["twelve_gross_negligence", "signal_violation", "center_line", "crosswalk", "drunk_driving", "unlicensed"],
    },
    {
        "title": "어린이보호구역 사고 및 민식이법 검토",
        "doc_type": "law_seed",
        "summary": "어린이보호구역에서 어린이 상해 사고가 발생한 경우 가중처벌 위험 검토",
        "raw_text": "어린이보호구역에서 운전자가 제한속도와 어린이 안전에 유의할 의무를 위반하여 어린이에게 상해를 입힌 경우 특정범죄 가중처벌 등에 관한 법률상 가중처벌 위험을 검토해야 한다. 어린이 여부, 보호구역 여부, 제한속도, 감속 여부, 상해 발생 여부가 핵심 사실이다.",
        "keywords": ["어린이보호구역", "민식이법", "어린이", "상해", "제한속도"],
        "scenario_tags": ["school_zone", "child_protection", "speed_limit", "injury"],
    },
    {
        "title": "횡단보도 보행자 보호의무",
        "doc_type": "law_seed",
        "summary": "횡단보도와 보행자 사고에서 운전자의 주의의무 검토",
        "raw_text": "횡단보도 또는 보행자가 통행 중인 구간에서는 운전자의 일시정지 및 보행자 보호의무가 중요하다. 보행자 충돌, 횡단보도 접근, 신호 상태, 시야 확보 여부, 감속 여부를 확인해야 한다.",
        "keywords": ["횡단보도", "보행자", "보행자 보호의무", "일시정지"],
        "scenario_tags": ["crosswalk", "pedestrian", "injury"],
    },
    {
        "title": "차선변경 및 진로변경 주의의무",
        "doc_type": "law_seed",
        "summary": "차선변경 사고에서 방향지시등, 안전거리, 사각지대 확인",
        "raw_text": "진로를 변경하려는 차량은 다른 차량의 정상 진행을 방해하지 않도록 방향지시등을 켜고 안전거리와 사각지대를 확인해야 한다. 급격한 변경, 방향지시등 미사용, 측면충돌은 과실 조정 요소가 된다.",
        "keywords": ["차선변경", "진로변경", "방향지시등", "사각지대", "측면충돌"],
        "scenario_tags": ["lane_change", "turn_signal", "blind_spot"],
    },
    {
        "title": "사고 후 조치 및 신고 의무",
        "doc_type": "law_seed",
        "summary": "사고 발생 후 구호, 위험방지, 신고 필요성",
        "raw_text": "교통사고가 발생하면 운전자는 사상자 구호와 위험 방지 조치를 해야 하며, 인명피해가 있거나 필요한 경우 경찰 신고를 검토해야 한다. 사고 현장을 이탈하거나 구호조치를 하지 않은 경우 도주 또는 사고 후 미조치 리스크가 있다.",
        "keywords": ["사고 후 조치", "신고의무", "구호조치", "뺑소니", "인명피해"],
        "scenario_tags": ["reporting_duty", "hit_and_run", "injury"],
    },
    {
        "title": "자전거 교통사고 주의의무",
        "doc_type": "law_seed",
        "summary": "자동차와 자전거 사고에서 취약 교통참여자 보호 및 통행 위치 검토",
        "raw_text": "자동차와 자전거가 관련된 사고에서는 자전거의 통행 위치, 자전거도로 또는 교차로 진입 방식, 자동차의 전방주시와 안전거리, 취약 교통참여자 보호 필요성을 함께 검토해야 한다.",
        "keywords": ["자전거", "자전거도로", "차대자전거", "전방주시", "취약 교통참여자"],
        "scenario_tags": ["bicycle", "vulnerable_road_user", "safe_distance"],
    },
]


def collect_traffic_law_documents() -> tuple[list[NormalizedLegalDocument], str]:
    docs: list[NormalizedLegalDocument] = []
    provider = "local_seed"
    if os.getenv("LAW_API_OC"):
        for item in fetch_road_traffic_law_articles(limit=80):
            docs.append(normalize_law_detail_article(item))
        if docs:
            provider = "law_api_detail" if any(not doc.metadata.get("detail_fetch_failed") for doc in docs) else "law_api"
        else:
            for query in TRAFFIC_LAW_QUERIES:
                for item in fetch_law_search(query, limit=5):
                    docs.append(normalize_law_api_item(item, query))
        if docs and provider != "law_api_detail":
            provider = "law_api"
    if not docs:
        docs = [normalize_seed_document(item) for item in LOCAL_SEED_DOCUMENTS]
    return docs, provider


def ingest_traffic_law_documents() -> dict[str, Any]:
    if not DB_URL:
        raise RuntimeError("DATABASE_URL is empty")
    docs, provider = collect_traffic_law_documents()
    inserted_documents = 0
    inserted_chunks = 0
    run_id = None
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO kb_ingest_runs(provider,status) VALUES(%s,'running') RETURNING id", (provider,))
            run_id = cur.fetchone()[0]
            try:
                for doc in docs:
                    cur.execute(
                        """
                        INSERT INTO kb_sources(name, source_type, source_uri, provider, version_tag, metadata)
                        VALUES(%s,%s,%s,%s,%s,%s)
                        RETURNING id
                        """,
                        (doc.source_name, doc.source_type, doc.source_uri, doc.provider, "traffic-law-v1", Jsonb(doc.metadata)),
                    )
                    source_id = cur.fetchone()[0]
                    cur.execute(
                        """
                        INSERT INTO kb_documents(source_id,title,doc_type,jurisdiction,effective_date,raw_text,summary,metadata,tsv)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,to_tsvector('simple', %s))
                        RETURNING id
                        """,
                        (
                            source_id,
                            doc.title,
                            doc.doc_type,
                            doc.jurisdiction,
                            doc.effective_date,
                            doc.raw_text,
                            doc.summary,
                            Jsonb({**doc.metadata, "keywords": doc.keywords, "scenario_tags": doc.scenario_tags}),
                            doc.raw_text,
                        ),
                    )
                    document_id = cur.fetchone()[0]
                    inserted_documents += 1
                    for chunk in chunk_legal_document(doc):
                        cur.execute(
                            """
                            INSERT INTO kb_chunks(
                              document_id, chunk_index, chunk_text, chunk_summary, article_no, clause_no,
                              scenario_tags, keywords, metadata, tsv,
                              plain_summary, related_reason, display_priority, source_url, law_name, article_title
                            )
                            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,to_tsvector('simple', %s),%s,%s,%s,%s,%s,%s)
                            ON CONFLICT(document_id, chunk_index) DO UPDATE
                              SET chunk_text=EXCLUDED.chunk_text,
                                  chunk_summary=EXCLUDED.chunk_summary,
                                  article_no=EXCLUDED.article_no,
                                  clause_no=EXCLUDED.clause_no,
                                  scenario_tags=EXCLUDED.scenario_tags,
                                  keywords=EXCLUDED.keywords,
                                  metadata=EXCLUDED.metadata,
                                  tsv=EXCLUDED.tsv,
                                  plain_summary=EXCLUDED.plain_summary,
                                  related_reason=EXCLUDED.related_reason,
                                  display_priority=EXCLUDED.display_priority,
                                  source_url=EXCLUDED.source_url,
                                  law_name=EXCLUDED.law_name,
                                  article_title=EXCLUDED.article_title
                            RETURNING id, chunk_text
                            """,
                            (
                                document_id,
                                chunk["chunk_index"],
                                chunk["chunk_text"],
                                chunk["chunk_summary"],
                                chunk["article_no"],
                                chunk["clause_no"],
                                chunk["scenario_tags"],
                                chunk["keywords"],
                                Jsonb(chunk["metadata"]),
                                chunk["chunk_text"],
                                chunk.get("plain_summary") or chunk["chunk_summary"],
                                chunk.get("related_reason") or "입력 사고와 연결되는 법률 근거입니다.",
                                int(chunk.get("display_priority") or 100),
                                chunk.get("source_url"),
                                chunk.get("law_name"),
                                chunk.get("article_title"),
                            ),
                        )
                        chunk_id, chunk_text = cur.fetchone()
                        vec, model = vectorize_text(chunk_text)
                        cur.execute(
                            """
                            INSERT INTO kb_embeddings(chunk_id, embedding, embedding_model)
                            VALUES(%s,%s::vector,%s)
                            ON CONFLICT(chunk_id) DO UPDATE
                              SET embedding=EXCLUDED.embedding,
                                  embedding_model=EXCLUDED.embedding_model,
                                  created_at=now()
                            """,
                            (chunk_id, vec, model),
                        )
                        inserted_chunks += 1
                cur.execute(
                    """
                    UPDATE kb_ingest_runs
                    SET status='succeeded', inserted_documents=%s, inserted_chunks=%s, finished_at=now()
                    WHERE id=%s
                    """,
                    (inserted_documents, inserted_chunks, run_id),
                )
                conn.commit()
            except Exception as exc:
                conn.rollback()
                with psycopg.connect(DB_URL) as err_conn:
                    with err_conn.cursor() as err_cur:
                        err_cur.execute(
                            "UPDATE kb_ingest_runs SET status='failed', error_message=%s, finished_at=now() WHERE id=%s",
                            (str(exc), run_id),
                        )
                        err_conn.commit()
                raise
    return {"run_id": str(run_id), "provider": provider, "inserted_documents": inserted_documents, "inserted_chunks": inserted_chunks}
