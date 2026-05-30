import type { FastifyInstance } from "fastify";
import { callInternalAgent } from "../lib/internal-client.js";

export type KniaRouteOptions = {
  env: any;
  db: any;
  requireAdmin: (req: any, reply: any) => any;
  errorPayload: (code: string, message: string, traceId: string) => any;
};

function cleanKniaPublicText(value: any, fallback: string) {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  if (!text) return fallback;
  if (text.length > 420 || text.includes("과실비율의 이해 과실비율 인정기준") || text.includes(" Main ")) return fallback;
  return text;
}

function summarizeRankingDetailStatus(rows: any[]) {
  const total = rows.length;
  const detailReady = rows.filter((row: any) => !!row.has_detail).length;
  const missing = Math.max(total - detailReady, 0);
  return {
    displayed_count: total,
    detail_ready_count: detailReady,
    detail_missing_count: missing,
    detail_ready_ratio: total ? Math.round((detailReady / total) * 100) : 0,
    needs_detail_collection: missing > 0,
  };
}

function publicKniaThumbnail(value: any) {
  const text = String(value ?? "").trim();
  const lowered = text.toLowerCase();
  if (!text || lowered.includes("logo_test.jpg") || lowered.includes("/images/common/logo_test")) {
    return null;
  }
  return text;
}

const KNIA_RANKING_CATEGORIES = [
  { label: "전체", value: "all", source_value: "전체" },
  { label: "차대차", value: "car_vs_car", source_value: "차대차" },
  { label: "차대사람", value: "car_vs_person", source_value: "차대사람" },
  { label: "차대자전거", value: "car_vs_bicycle", source_value: "차대자전거" }
];

const KNIA_PARTY_LABELS: Record<string, string> = {
  car_vs_car: "차대차 사고",
  car_vs_person: "차대보행자 사고",
  car_vs_bicycle: "차대자전거 사고",
  single_vehicle: "단독 사고",
  car_vs_object: "물체/시설물 사고",
  unknown: "확인이 필요합니다."
};

function normalizeKniaRankingQuery(value: unknown) {
  const raw = String(value ?? "").trim();
  if (!raw) return "";
  try {
    return decodeURIComponent(raw).replace(/\s+/g, " ").trim().slice(0, 120);
  } catch {
    return raw.replace(/\s+/g, " ").trim().slice(0, 120);
  }
}

function parameter(params: any[], value: any) {
  params.push(value);
  return `$${params.length}`;
}

function kniaPartyFromChartNo(value: unknown) {
  const chartNo = String(value ?? "").trim();
  if (chartNo.startsWith("차")) return "car_vs_car";
  if (chartNo.startsWith("보")) return "car_vs_person";
  if (chartNo.startsWith("자") || chartNo.startsWith("거")) return "car_vs_bicycle";
  if (chartNo.startsWith("단")) return "single_vehicle";
  if (chartNo.startsWith("기") || chartNo.startsWith("물")) return "car_vs_object";
  return "";
}

function normalizeKniaRankingParty(input: { accident_party_type?: any; chart_no?: any; source_category?: any }) {
  const byPrefix = kniaPartyFromChartNo(input.chart_no);
  if (byPrefix) return byPrefix;
  const raw = String(input.accident_party_type ?? "").trim();
  if (raw && raw !== "unknown") return raw;
  const source = String(input.source_category ?? "").trim();
  if (source.includes("차대자전거") || source.includes("자전거")) return "car_vs_bicycle";
  if (source.includes("차대사람") || source.includes("보행")) return "car_vs_person";
  if (source.includes("차대차")) return "car_vs_car";
  return raw || "unknown";
}

function kniaRankingPartyLabel(input: { accident_party_label?: any; accident_party_type?: any; chart_no?: any; source_category?: any }) {
  const existing = String(input.accident_party_label ?? "").trim();
  if (existing && existing !== "확인이 필요합니다." && existing !== "사고유형 확인 필요") return existing;
  const party = normalizeKniaRankingParty(input);
  return KNIA_PARTY_LABELS[party] ?? KNIA_PARTY_LABELS.unknown;
}

function rankingSourceCategoryForParty(party: string) {
  return KNIA_RANKING_CATEGORIES.find((item) => item.value === party)?.source_value ?? "";
}

function buildKniaRankingPartyClause(alias: string, params: any[], accidentPartyType: string, sourceAlias?: string) {
  if (!accidentPartyType || accidentPartyType === "all") return "";
  const partyParam = parameter(params, accidentPartyType);
  const sourceLabel = rankingSourceCategoryForParty(accidentPartyType);
  const sourceClause = sourceAlias && sourceLabel ? ` OR ${sourceAlias}.source_category=${parameter(params, sourceLabel)}` : "";

  if (accidentPartyType === "car_vs_car") {
    return ` AND (${alias}.accident_party_type=${partyParam} OR ${alias}.chart_no LIKE '차%'${sourceClause})`;
  }
  if (accidentPartyType === "car_vs_person") {
    return ` AND (${alias}.accident_party_type=${partyParam} OR ${alias}.chart_no LIKE '보%'${sourceClause})`;
  }
  if (accidentPartyType === "car_vs_bicycle") {
    return ` AND (${alias}.accident_party_type=${partyParam} OR ${alias}.chart_no LIKE '자%' OR ${alias}.chart_no LIKE '거%'${sourceClause})`;
  }
  if (accidentPartyType === "single_vehicle") {
    return ` AND (${alias}.accident_party_type=${partyParam} OR ${alias}.chart_no LIKE '단%'${sourceClause})`;
  }
  return ` AND (${alias}.accident_party_type=${partyParam}${sourceClause})`;
}

function rankingSearchTerms(q: string, accidentPartyType: string) {
  const terms = [q].filter(Boolean);
  const isBicycleQuery = accidentPartyType === "car_vs_bicycle" || /자전거|차대자전거|bike|bicycle/i.test(q);
  if (isBicycleQuery) {
    for (const term of ["자전거", "차대자전거", "자전거도로", "자전거 사고"]) {
      if (!terms.includes(term)) terms.push(term);
    }
  }
  return terms;
}

function buildKniaRankingSearchClause(params: any[], q: string, accidentPartyType: string) {
  if (!q) return "";
  const includesBicyclePrefix = /자전거|차대자전거|bike|bicycle/i.test(q);
  const clauses = rankingSearchTerms(q, accidentPartyType).map((term) => {
    const like = parameter(params, `%${term}%`);
    return `(
      r.chart_no ILIKE ${like}
      OR r.title ILIKE ${like}
      OR COALESCE(r.source_category, '') ILIKE ${like}
      OR COALESCE(r.source_url, '') ILIKE ${like}
      OR COALESCE(r.source_detail_url, '') ILIKE ${like}
      OR COALESCE(c.accident_summary, '') ILIKE ${like}
      OR COALESCE(c.basic_fault_text, '') ILIKE ${like}
      OR COALESCE(c.display_tags::text, '') ILIKE ${like}
      OR COALESCE(c.category_path::text, '') ILIKE ${like}
    )`;
  });
  const prefixFallback = includesBicyclePrefix ? " OR r.chart_no LIKE '자%' OR r.chart_no LIKE '거%'" : "";
  return ` AND (${clauses.join(" OR ")}${prefixFallback})`;
}

function buildKniaChartFallbackSearchClause(params: any[], q: string, accidentPartyType: string) {
  if (!q) return "";
  const includesBicyclePrefix = /자전거|차대자전거|bike|bicycle/i.test(q);
  const clauses = rankingSearchTerms(q, accidentPartyType).map((term) => {
    const like = parameter(params, `%${term}%`);
    return `(
      c.chart_no ILIKE ${like}
      OR c.title ILIKE ${like}
      OR COALESCE(c.accident_summary, '') ILIKE ${like}
      OR COALESCE(c.basic_fault_text, '') ILIKE ${like}
      OR COALESCE(c.display_tags::text, '') ILIKE ${like}
      OR COALESCE(c.category_path::text, '') ILIKE ${like}
      OR COALESCE(c.source_url, '') ILIKE ${like}
      OR COALESCE(c.source_detail_url, '') ILIKE ${like}
    )`;
  });
  const prefixFallback = includesBicyclePrefix ? " OR c.chart_no LIKE '자%' OR c.chart_no LIKE '거%'" : "";
  return ` AND (${clauses.join(" OR ")}${prefixFallback})`;
}

function normalizeKniaRankingRow(row: any) {
  const party = normalizeKniaRankingParty(row);
  const chartType = row.chart_type ?? "1";
  const chartNo = row.chart_no;
  const localUrl = row.local_chart_url ?? row.chart_url ?? `/knia/charts/${encodeURIComponent(chartNo)}?chartType=${encodeURIComponent(chartType)}`;
  return {
    rank: row.rank == null ? null : Number(row.rank),
    rank_no: row.rank == null ? null : Number(row.rank),
    chart_no: chartNo,
    chart_type: chartType,
    title: row.title || `KNIA 과실비율 인정기준 ${chartNo}`,
    search_count: row.search_count == null ? null : Number(row.search_count),
    percentage: row.percentage == null ? null : Number(row.percentage),
    source_category: row.source_category || rankingSourceCategoryForParty(party) || "전체",
    accident_party_type: party,
    accident_party_label: kniaRankingPartyLabel(row),
    source_url: row.source_url,
    source_detail_url: row.source_detail_url,
    local_chart_url: localUrl,
    source_onclick: row.source_onclick,
    chart_url: localUrl,
    has_detail: !!row.has_detail,
    base_fault_a: row.base_fault_a == null ? null : Number(row.base_fault_a),
    base_fault_b: row.base_fault_b == null ? null : Number(row.base_fault_b),
    adjustment_factor_count: Number(row.adjustment_factor_count ?? 0),
    reference_section_count: Number(row.reference_section_count ?? 0),
    collected_at: row.collected_at,
    summary: row.summary ?? row.accident_summary ?? row.basic_fault_text ?? null,
    matched_by: row.matched_by ?? "ranking",
  };
}

export function registerKniaRoutes(app: FastifyInstance, opts: KniaRouteOptions) {
  const { env, db, errorPayload } = opts;

  async function callInternalAgentGet(path: string, traceId: string) {
    const res = await fetch(`${env.agentUrl}${path}`, {
      method: "GET",
      headers: {
        "x-internal-token": env.internalToken,
        "x-correlation-id": traceId
      }
    });
    if (!res.ok) throw new Error(`internal_agent_get_error_${res.status}:${(await res.text()).slice(0, 300)}`);
    return await res.json();
  }

  app.get(`${env.apiPrefix}/knia/ranking`, async (req, reply) => {
    const traceId = (req.headers["x-correlation-id"] as string) || "";
    const limit = Math.max(1, Math.min(Number((req.query as any)?.limit ?? 20) || 20, 50));
    const rawType = String((req.query as any)?.accidentPartyType ?? "all").trim() || "all";
    const q = normalizeKniaRankingQuery((req.query as any)?.q);
    const typeMap: Record<string, { value: string; source: string }> = {};
    for (const category of KNIA_RANKING_CATEGORIES) {
      typeMap[category.value] = { value: category.value, source: category.source_value };
      typeMap[category.source_value] = { value: category.value, source: category.source_value };
    }
    const selected = typeMap[rawType] ?? typeMap.all;

    let rankingError: unknown = null;
    let rows: any = { rowCount: 0, rows: [] };
    try {
      const params: any[] = [];
      const where = [
        "1=1",
        buildKniaRankingPartyClause("r", params, selected.value, "r"),
        buildKniaRankingSearchClause(params, q, selected.value),
      ].join(" ");
      const limitParam = parameter(params, limit);
      rows = await db.query(
        `SELECT r.rank, r.chart_no, r.chart_type, r.title,
                r.search_count, r.percentage, r.source_category,
                r.accident_party_type, r.source_url, r.source_detail_url,
                r.local_chart_url, r.source_onclick, r.chart_url,
                r.collected_at,
                c.accident_party_label, c.accident_summary, c.basic_fault_text,
                c.base_fault_a, c.base_fault_b,
                CASE WHEN c.detail_collected_at IS NOT NULL THEN true ELSE false END AS has_detail,
                (SELECT COUNT(*)::int FROM knia_adjustment_factors af
                  WHERE af.chart_no=r.chart_no AND af.chart_type=COALESCE(r.chart_type, '1')) AS adjustment_factor_count,
                (SELECT COUNT(*)::int FROM knia_chart_reference_sections rs
                  WHERE rs.chart_no=r.chart_no AND rs.chart_type=COALESCE(r.chart_type, '1')) AS reference_section_count,
                'ranking' AS matched_by
         FROM knia_ranking_items r
         LEFT JOIN knia_fault_charts c
           ON c.chart_no=r.chart_no AND c.chart_type=COALESCE(r.chart_type, '1')
         WHERE ${where}
         ORDER BY
           CASE WHEN $${params.length + 1}::text='car_vs_bicycle' AND (r.chart_no LIKE '자%' OR r.chart_no LIKE '거%') THEN 0 ELSE 1 END,
           r.rank ASC,
           r.chart_no ASC
         LIMIT ${limitParam}`,
        [...params, selected.value],
      );
    } catch (err) {
      rankingError = err;
      req.log?.error?.({ err, trace_id: traceId, q, accidentPartyType: selected.value }, "KNIA ranking query failed");
    }

    let items = (rows.rows ?? []).map(normalizeKniaRankingRow);

    if (!items.length) {
      try {
        const params: any[] = [];
        const where = [
          "1=1",
          buildKniaRankingPartyClause("c", params, selected.value),
          buildKniaChartFallbackSearchClause(params, q, selected.value),
        ].join(" ");
        const limitParam = parameter(params, limit);
        const fallbackRows = await db.query(
          `SELECT NULL::int AS rank,
                  c.chart_no, c.chart_type, c.title,
                  NULL::int AS search_count, NULL::numeric AS percentage,
                  c.accident_party_type, c.accident_party_label,
                  c.source_url, c.source_detail_url,
                  NULL::text AS local_chart_url, NULL::text AS source_onclick, NULL::text AS chart_url,
                  c.updated_at AS collected_at,
                  c.accident_summary, c.basic_fault_text,
                  c.base_fault_a, c.base_fault_b,
                  CASE WHEN c.detail_collected_at IS NOT NULL THEN true ELSE false END AS has_detail,
                  (SELECT COUNT(*)::int FROM knia_adjustment_factors af
                    WHERE af.chart_no=c.chart_no AND af.chart_type=COALESCE(c.chart_type, '1')) AS adjustment_factor_count,
                  (SELECT COUNT(*)::int FROM knia_chart_reference_sections rs
                    WHERE rs.chart_no=c.chart_no AND rs.chart_type=COALESCE(c.chart_type, '1')) AS reference_section_count,
                  'chart_fallback' AS matched_by
           FROM knia_fault_charts c
           WHERE ${where}
           ORDER BY
             CASE WHEN $${params.length + 1}::text='car_vs_bicycle' AND (c.chart_no LIKE '자%' OR c.chart_no LIKE '거%') THEN 0 ELSE 1 END,
             c.detail_collected_at DESC NULLS LAST,
             c.updated_at DESC NULLS LAST,
             c.chart_no ASC
           LIMIT ${limitParam}`,
          [...params, selected.value],
        );
        items = (fallbackRows.rows ?? []).map(normalizeKniaRankingRow);
      } catch (err) {
        req.log?.error?.({ err, rankingError, trace_id: traceId, q, accidentPartyType: selected.value }, "KNIA ranking fallback query failed");
        return reply.send({
          items: [],
          categories: KNIA_RANKING_CATEGORIES,
          total: 0,
          query: q,
          accident_party_type: selected.value,
          detail_summary: summarizeRankingDetailStatus([]),
          trace_id: traceId,
          empty_message: "관련 기준을 찾지 못했습니다. 검색어를 바꿔 다시 시도해 주세요.",
          error: errorPayload("KNIA_RANKING_UNAVAILABLE", "검색 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.", traceId).error,
        });
      }
    }

    return reply.send({
      items,
      categories: KNIA_RANKING_CATEGORIES,
      total: items.length,
      query: q,
      accident_party_type: selected.value,
      detail_summary: summarizeRankingDetailStatus(items),
      trace_id: traceId,
      empty_message: items.length === 0 ? "관련 기준을 찾지 못했습니다. 검색어를 바꿔 다시 시도해 주세요." : undefined,
      ...(rankingError && items.length ? { warning: { code: "KNIA_RANKING_FALLBACK_USED", message: "검색순위 대신 상세 기준에서 결과를 찾았습니다." } } : {}),
    });
  });

  app.get(`${env.apiPrefix}/knia/charts/:chartNo`, async (req, reply) => {
    const traceId = req.headers["x-correlation-id"] as string;
    const chartNo = decodeURIComponent(String((req.params as any).chartNo));
    const chartType = String((req.query as any)?.chartType ?? "1");
    const row = await db.query(
      `SELECT chart_no, chart_type, title, vehicle_a_label, vehicle_b_label, category_path,
              accident_summary, applicable_text, non_applicable_text, basic_fault_text,
              base_fault_a, base_fault_b, applied_fault_a, applied_fault_b,
              accident_explanation, accident_situation_lines, adjustment_factors,
              adjustment_explanations, related_laws, case_references,
              source_url, source_detail_url, thumbnail_url, video_url, media_embed_url,
              media_provider, license_status, attribution, updated_at,
              accident_party_type, accident_party_label, vehicle_a_role, vehicle_b_role,
              vulnerable_road_user_type, object_type, scenario_summary_easy,
              recommended_user_actions, display_tags, detail_collected_at
       FROM knia_fault_charts
       WHERE chart_no=$1 AND chart_type=$2
       LIMIT 1`,
      [chartNo, chartType]
    ).catch(() => ({ rowCount: 0, rows: [] as any[] }));
    if (!row.rowCount) {
      const rankingRow = await db.query(
        `SELECT chart_no, COALESCE(chart_type, '1') AS chart_type, title, source_category,
                accident_party_type, source_url, source_detail_url, local_chart_url, chart_url, collected_at
         FROM knia_ranking_items
         WHERE chart_no=$1 AND COALESCE(chart_type, '1')=$2
         ORDER BY collected_at DESC, rank ASC
         LIMIT 1`,
        [chartNo, chartType]
      ).catch(() => ({ rowCount: 0, rows: [] as any[] }));
      if (!rankingRow.rowCount) {
        return reply.code(404).send(errorPayload("KNIA_CHART_NOT_FOUND", "과실비율 기준을 찾을 수 없습니다. 먼저 KNIA 수집을 실행해 주세요.", traceId));
      }
      const ranking = rankingRow.rows[0];
      const sourceDetailUrl = ranking.source_detail_url || ranking.source_url;
      return {
        chart: {
          chart_no: ranking.chart_no,
          chart_type: ranking.chart_type,
          title: ranking.title || `KNIA 과실비율 인정기준 ${ranking.chart_no}`,
          vehicle_a_label: null,
          vehicle_b_label: null,
          category_path: [ranking.source_category].filter(Boolean),
          accident_party_type: ranking.accident_party_type ?? "unknown",
          accident_party_label: ranking.source_category ?? "사고유형 확인 필요",
          vehicle_a_role: null,
          vehicle_b_role: null,
          vulnerable_road_user_type: null,
          object_type: null,
          scenario_summary_easy: "검색순위에는 포함되어 있지만 상세 기준 본문은 아직 로컬 DB에 수집되지 않았습니다.",
          recommended_user_actions: ["관리자 권한으로 상세 기준 수집을 실행한 뒤 다시 확인해 주세요."],
          display_tags: ["ranking_only"],
          accident_summary: "검색순위에는 포함되어 있지만 상세 기준 본문은 아직 로컬 DB에 수집되지 않았습니다.",
          applicable_text: "상세 기준 수집 후 KNIA 원문 적용 조건을 표시합니다.",
          non_applicable_text: "상세 기준 수집 후 예외 조건과 주의 사항을 표시합니다.",
          basic_fault_text: "상세 기준 수집 후 기본 과실비율을 표시합니다.",
          base_fault_a: null,
          base_fault_b: null,
          applied_fault_a: null,
          applied_fault_b: null,
          accident_explanation: "상세 기준 수집이 필요한 KNIA 검색순위 항목입니다.",
          accident_situation_lines: [],
          adjustment_factors: [],
          adjustment_explanations: [],
          related_laws: [],
          case_references: [],
          source_url: ranking.source_url,
          source_detail_url: sourceDetailUrl,
          thumbnail_url: null,
          video_url: null,
          media_embed_url: null,
          media_provider: "external_url",
          related_video: {
            display_mode: "external_link",
            source_url: sourceDetailUrl || ranking.source_url,
            embed_url: null,
            thumbnail_url: null,
            button_label: "KNIA 원문 기준 보기",
            attribution: "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털"
          },
          license_status: "source_link_only",
          attribution: "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털",
          updated_at: ranking.collected_at,
          detail_collected_at: null,
          is_ranking_placeholder: true,
          adjustment_summary: {
            adjustment_factor_count: 0,
            adjustment_explanation_count: 0,
            related_law_count: 0,
            case_reference_count: 0,
          }
        },
        trace_id: traceId
      };
    }
    const chart = row.rows[0];
    return {
      chart: {
        chart_no: chart.chart_no,
        chart_type: chart.chart_type,
        title: chart.title,
        vehicle_a_label: chart.vehicle_a_label,
        vehicle_b_label: chart.vehicle_b_label,
        category_path: chart.category_path ?? [],
        accident_party_type: chart.accident_party_type ?? "unknown",
        accident_party_label: chart.accident_party_label ?? "사고유형 확인 필요",
        vehicle_a_role: chart.vehicle_a_role,
        vehicle_b_role: chart.vehicle_b_role,
        vulnerable_road_user_type: chart.vulnerable_road_user_type,
        object_type: chart.object_type,
        scenario_summary_easy: chart.scenario_summary_easy,
        recommended_user_actions: chart.recommended_user_actions ?? [],
        display_tags: chart.display_tags ?? [],
        accident_summary: chart.accident_summary,
        applicable_text: cleanKniaPublicText(chart.applicable_text, chart.accident_summary ?? "원문 기준에서 상세 적용 조건을 확인해 주세요."),
        non_applicable_text: cleanKniaPublicText(chart.non_applicable_text, "급정거, 끼어들기 직후 사고 등 세부 상황에 따라 다른 기준이 적용될 수 있습니다."),
        basic_fault_text: cleanKniaPublicText(chart.basic_fault_text, "기본 과실은 사고 상황에 따라 달라질 수 있습니다."),
        base_fault_a: chart.base_fault_a,
        base_fault_b: chart.base_fault_b,
        applied_fault_a: chart.applied_fault_a,
        applied_fault_b: chart.applied_fault_b,
        accident_explanation: chart.accident_explanation,
        accident_situation_lines: chart.accident_situation_lines ?? [],
        adjustment_factors: chart.adjustment_factors ?? [],
        adjustment_explanations: chart.adjustment_explanations ?? [],
        related_laws: chart.related_laws ?? [],
        case_references: chart.case_references ?? [],
        source_url: chart.source_url,
        source_detail_url: chart.source_detail_url ?? chart.source_url,
        thumbnail_url: publicKniaThumbnail(chart.thumbnail_url),
        video_url: chart.video_url,
        media_embed_url: chart.media_embed_url,
        media_provider: "external_url",
        related_video: {
          display_mode: "external_link",
          source_url: chart.video_url || chart.source_detail_url || chart.source_url,
          embed_url: null,
          thumbnail_url: publicKniaThumbnail(chart.thumbnail_url),
          button_label: chart.video_url ? "KNIA 관련 영상 보기" : "KNIA 원문 기준 보기",
          attribution: chart.attribution ?? "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털"
        },
        license_status: "source_link_only",
        attribution: chart.attribution ?? "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회 과실비율정보포털",
        updated_at: chart.updated_at,
        detail_collected_at: chart.detail_collected_at,
        adjustment_summary: {
          adjustment_factor_count: Array.isArray(chart.adjustment_factors) ? chart.adjustment_factors.length : 0,
          adjustment_explanation_count: Array.isArray(chart.adjustment_explanations) ? chart.adjustment_explanations.length : 0,
          related_law_count: Array.isArray(chart.related_laws) ? chart.related_laws.length : 0,
          case_reference_count: Array.isArray(chart.case_references) ? chart.case_references.length : 0,
        }
      },
      trace_id: traceId
    };
  });

  app.post(`${env.apiPrefix}/knia/match`, async (req, reply) => {
    const traceId = req.headers["x-correlation-id"] as string;
    try {
      const result = await callInternalAgent("/internal/v1/knia/match", req.body ?? {}, traceId, {
        baseUrl: env.agentUrl,
        internalToken: env.internalToken,
        timeoutMs: env.timeoutMs,
        retryCount: env.retryCount
      });
      const safeItems = (result.items ?? []).map((x: any) => ({
        chart_no: x.chart_no,
        chart_type: x.chart_type,
        title: x.title,
        accident_party_type: x.accident_party_type,
        accident_party_label: x.accident_party_label,
        display_tags: x.display_tags ?? [],
        recommended_user_actions: x.recommended_user_actions ?? [],
        match_label: x.match_label,
        match_reason: x.match_reason,
        base_fault_a: x.base_fault_a,
        base_fault_b: x.base_fault_b,
        accident_summary: x.accident_summary,
        basic_fault_text: x.basic_fault_text,
        source_url: x.source_url,
        thumbnail_url: x.thumbnail_url,
        video_url: x.video_url,
        media: x.media,
        attribution: x.attribution
      }));
      return { items: safeItems, source: "과실비율정보포털", trace_id: traceId };
    } catch {
      return reply.code(502).send(errorPayload("KNIA_MATCH_FAILED", "과실비율 기준 매칭에 실패했습니다.", traceId));
    }
  });

  app.post(`${env.apiPrefix}/knia/fault/estimate`, async (req, reply) => {
    const traceId = req.headers["x-correlation-id"] as string;
    try {
      const result = await callInternalAgent("/internal/v1/knia/fault/estimate", req.body ?? {}, traceId, {
        baseUrl: env.agentUrl,
        internalToken: env.internalToken,
        timeoutMs: env.timeoutMs,
        retryCount: env.retryCount
      });
      return { ...result, trace_id: traceId };
    } catch (err: any) {
      return reply.code(502).send(errorPayload("KNIA_FAULT_ESTIMATE_FAILED", err?.message || "KNIA 가감요소 기반 과실 산정에 실패했습니다.", traceId));
    }
  });

  app.get(`${env.apiPrefix}/knia/charts/:chartNo/adjustments`, async (req, reply) => {
    const traceId = req.headers["x-correlation-id"] as string;
    const chartNo = decodeURIComponent(String((req.params as any).chartNo));
    const chartType = String((req.query as any)?.chartType ?? "1");
    const rows = await db.query(
      `SELECT label, condition_code, checkbox_value, delta_a, delta_b, source_case_id, factor_order, source_detail_url
       FROM knia_adjustment_factors
       WHERE chart_no=$1 AND chart_type=$2
       ORDER BY factor_order ASC, id ASC`,
      [chartNo, chartType]
    );
    return { chart_no: chartNo, chart_type: chartType, items: rows.rows, trace_id: traceId };
  });

  app.get(`${env.apiPrefix}/knia/charts/:chartNo/references`, async (req, reply) => {
    const traceId = req.headers["x-correlation-id"] as string;
    const chartNo = decodeURIComponent(String((req.params as any).chartNo));
    const chartType = String((req.query as any)?.chartType ?? "1");
    const rows = await db.query(
      `SELECT section_type, title, body, law_title, law_text, case_title, case_body, decision_summary, item_order, source_detail_url
       FROM knia_chart_reference_sections
       WHERE chart_no=$1 AND chart_type=$2
       ORDER BY section_type ASC, item_order ASC, id ASC`,
      [chartNo, chartType]
    );
    const grouped: any = { adjustment_explanations: [], related_laws: [], case_references: [] };
    for (const row of rows.rows) {
      if (row.section_type === "adjustment_explanation") grouped.adjustment_explanations.push(row);
      if (row.section_type === "related_law") grouped.related_laws.push(row);
      if (row.section_type === "case_reference") grouped.case_references.push(row);
    }
    return { chart_no: chartNo, chart_type: chartType, ...grouped, trace_id: traceId };
  });

  app.get(`${env.apiPrefix}/knia/myaccident-pages`, async (req, reply) => {
    const traceId = req.headers["x-correlation-id"] as string;
    try {
      const result = await callInternalAgentGet("/internal/v1/knia/myaccident-pages", traceId);
      return { items: result.items ?? [], trace_id: traceId };
    } catch {
      return reply.code(502).send(errorPayload("KNIA_MENU_FAILED", "KNIA 메뉴 목록을 불러오지 못했습니다.", traceId));
    }
  });

  app.get(`${env.apiPrefix}/knia/myaccident/:myaccidentNo/tree`, async (req, reply) => {
    const traceId = req.headers["x-correlation-id"] as string;
    const myaccidentNo = Number((req.params as any).myaccidentNo);
    try {
      const result = await callInternalAgentGet(`/internal/v1/knia/myaccident/${myaccidentNo}/tree`, traceId);
      return { ...result, trace_id: traceId };
    } catch {
      return reply.code(502).send(errorPayload("KNIA_TREE_FAILED", "KNIA 사고유형 트리를 불러오지 못했습니다.", traceId));
    }
  });

  app.get(`${env.apiPrefix}/knia/json/search`, async (req, reply) => {
    const traceId = req.headers["x-correlation-id"] as string;
    const q = String((req.query as any)?.q ?? "");
    const accidentPartyType = String((req.query as any)?.accidentPartyType ?? "");
    const limit = Math.min(Number((req.query as any)?.limit ?? 5), 20);
    try {
      const path = `/internal/v1/knia/json/search?q=${encodeURIComponent(q)}&limit=${limit}${accidentPartyType ? `&accidentPartyType=${encodeURIComponent(accidentPartyType)}` : ""}`;
      const result = await callInternalAgentGet(path, traceId);
      const items = (result.items ?? []).map((x: any) => ({
        title: x.title,
        summary: x.summary,
        source_url: x.source_url,
        accident_party_label: x.accident_party_label,
        display_tags: x.display_tags ?? [],
        attribution: x.attribution ?? "자료 출처: 손해보험협회 자동차사고 과실비율 분쟁심의위원회"
      }));
      return { items, cache: result.cache ? { exact_hit: !!result.cache.exact_hit, semantic_hit: !!result.cache.semantic_hit } : undefined, trace_id: traceId };
    } catch {
      return reply.code(502).send(errorPayload("KNIA_JSON_SEARCH_FAILED", "KNIA JSON 검색에 실패했습니다.", traceId));
    }
  });

  app.get(`${env.apiPrefix}/knia/media/search`, async (req, reply) => {
    const traceId = req.headers["x-correlation-id"] as string;
    const q = String((req.query as any)?.q ?? "");
    const accidentPartyType = String((req.query as any)?.accidentPartyType ?? "");
    try {
      const path = `/internal/v1/knia/media/search?q=${encodeURIComponent(q)}${accidentPartyType ? `&accidentPartyType=${encodeURIComponent(accidentPartyType)}` : ""}`;
      const result = await callInternalAgentGet(path, traceId);
      return { items: result.items ?? [], trace_id: traceId };
    } catch {
      return reply.code(502).send(errorPayload("KNIA_MEDIA_SEARCH_FAILED", "KNIA 영상/문서 검색에 실패했습니다.", traceId));
    }
  });

}
