import type { FastifyInstance } from "fastify";
import { callInternalAgent } from "../lib/internal-client.js";
import { requireUser } from "../lib/request-guards.js";

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

export function registerKniaRoutes(app: FastifyInstance, opts: KniaRouteOptions) {
  const { env, db, requireAdmin, errorPayload } = opts;

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
    const traceId = req.headers["x-correlation-id"] as string;
    const limit = Math.min(Number((req.query as any)?.limit ?? 20), 50);
    const rawType = String((req.query as any)?.accidentPartyType ?? "all").trim() || "all";
    const q = String((req.query as any)?.q ?? "").trim();
    const categories = [
      { label: "\uC804\uCCB4", value: "all", source_value: "\uC804\uCCB4" },
      { label: "\uCC28\uB300\uCC28", value: "car_vs_car", source_value: "\uCC28\uB300\uCC28" },
      { label: "\uCC28\uB300\uC0AC\uB78C", value: "car_vs_person", source_value: "\uCC28\uB300\uC0AC\uB78C" },
      { label: "\uCC28\uB300\uC790\uC804\uAC70", value: "car_vs_bicycle", source_value: "\uCC28\uB300\uC790\uC804\uAC70" }
    ];
    const typeMap: Record<string, { value: string; source: string }> = {};
    for (const category of categories) {
      typeMap[category.value] = { value: category.value, source: category.source_value };
      typeMap[category.source_value] = { value: category.value, source: category.source_value };
    }
    const selected = typeMap[rawType] ?? typeMap.all;
    const params: any[] = [selected.source];
    let where = `source_category=$1`;
    if (q) {
      params.push(`%${q}%`);
      where += ` AND (title ILIKE $${params.length} OR chart_no ILIKE $${params.length})`;
    }
    params.push(limit);
    const rows = await db.query(
      `SELECT knia_ranking_items.rank, knia_ranking_items.chart_no, knia_ranking_items.chart_type, knia_ranking_items.title,
              knia_ranking_items.search_count, knia_ranking_items.percentage, knia_ranking_items.source_category,
              knia_ranking_items.accident_party_type, knia_ranking_items.source_url, knia_ranking_items.source_detail_url,
              knia_ranking_items.local_chart_url, knia_ranking_items.source_onclick, knia_ranking_items.chart_url,
              knia_ranking_items.collected_at,
              c.base_fault_a, c.base_fault_b,
              CASE WHEN c.detail_collected_at IS NOT NULL THEN true ELSE false END AS has_detail,
              (SELECT COUNT(*)::int FROM knia_adjustment_factors af
                WHERE af.chart_no=knia_ranking_items.chart_no AND af.chart_type=COALESCE(knia_ranking_items.chart_type, '1')) AS adjustment_factor_count,
              (SELECT COUNT(*)::int FROM knia_chart_reference_sections rs
                WHERE rs.chart_no=knia_ranking_items.chart_no AND rs.chart_type=COALESCE(knia_ranking_items.chart_type, '1')) AS reference_section_count
       FROM knia_ranking_items
       LEFT JOIN knia_fault_charts c
         ON c.chart_no=knia_ranking_items.chart_no AND c.chart_type=COALESCE(knia_ranking_items.chart_type, '1')
       WHERE ${where}
       ORDER BY rank ASC
       LIMIT $${params.length}`,
      params,
    );
    return reply.send({
      items: rows.rows.map((row: any) => ({
        rank: Number(row.rank),
        rank_no: Number(row.rank),
        chart_no: row.chart_no,
        chart_type: row.chart_type ?? "1",
        title: row.title,
        search_count: row.search_count == null ? null : Number(row.search_count),
        percentage: row.percentage == null ? null : Number(row.percentage),
        source_category: row.source_category,
        accident_party_type: row.accident_party_type,
        source_url: row.source_url,
        source_detail_url: row.source_detail_url,
        local_chart_url: row.local_chart_url ?? row.chart_url ?? `/knia/charts/${encodeURIComponent(row.chart_no)}?chartType=${encodeURIComponent(row.chart_type ?? "1")}`,
        source_onclick: row.source_onclick,
        chart_url: row.chart_url ?? row.local_chart_url ?? `/knia/charts/${encodeURIComponent(row.chart_no)}?chartType=${encodeURIComponent(row.chart_type ?? "1")}`,
        has_detail: !!row.has_detail,
        base_fault_a: row.base_fault_a == null ? null : Number(row.base_fault_a),
        base_fault_b: row.base_fault_b == null ? null : Number(row.base_fault_b),
        adjustment_factor_count: Number(row.adjustment_factor_count ?? 0),
        reference_section_count: Number(row.reference_section_count ?? 0),
        collected_at: row.collected_at,
      })),
      categories,
      trace_id: traceId,
      empty_message: rows.rowCount === 0 ? "\uC544\uC9C1 \uC218\uC9D1\uB41C \uAC80\uC0C9\uC21C\uC704\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4. \uAD00\uB9AC\uC790 \uC218\uC9D1\uC744 \uBA3C\uC800 \uC2E4\uD589\uD558\uC138\uC694." : undefined,
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
            button_label: "KNIA 원문 보기",
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
        thumbnail_url: chart.thumbnail_url,
        video_url: chart.video_url,
        media_embed_url: chart.media_embed_url,
        media_provider: "external_url",
        related_video: {
          display_mode: chart.media_embed_url ? "embed" : "external_link",
          source_url: chart.video_url || chart.source_url,
          embed_url: chart.media_embed_url,
          thumbnail_url: chart.thumbnail_url,
          button_label: chart.video_url ? "관련 영상 보기" : "원문 기준 보기",
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

  app.post(`${env.apiPrefix}/admin/knia/collect`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    const traceId = req.headers["x-correlation-id"] as string;
    const body = (req.body ?? {}) as any;
    const rankingOnly = body.ranking === true && body.menu === false && body.charts === false;
    if (!rankingOnly && !requireAdmin(req as any, reply)) return;
    const result: any = {};
    try {
      if (body.menu !== false) result.menu = await callInternalAgent("/internal/v1/knia/collect/menu-pages", {}, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 180000, retryCount: 0 });
      if (body.ranking !== false) result.ranking = await callInternalAgent("/internal/v1/knia/collect/ranking", {}, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 180000, retryCount: 0 });
      if (body.charts !== false) result.charts = await callInternalAgent("/internal/v1/knia/collect/charts", { chart_nos: body.chart_nos, max_charts: body.max_charts }, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 240000, retryCount: 0 });
      return { result, trace_id: traceId };
    } catch (err: any) {
      return reply.code(502).send(errorPayload("KNIA_COLLECT_FAILED", err?.message || "KNIA 데이터 수집에 실패했습니다.", traceId));
    }
  });

  app.post(`${env.apiPrefix}/admin/knia/collect-ranking-details`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    if (!requireAdmin(req as any, reply)) return;
    const traceId = req.headers["x-correlation-id"] as string;
    try {
      const result = await callInternalAgent("/internal/v1/knia/collect/ranking-details", req.body ?? {}, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 600000, retryCount: 0 });
      return { result, trace_id: traceId };
    } catch (err: any) {
      return reply.code(502).send(errorPayload("KNIA_RANKING_DETAIL_COLLECT_FAILED", err?.message || "KNIA 상세 기준 수집에 실패했습니다.", traceId));
    }
  });

  app.post(`${env.apiPrefix}/admin/knia/rebuild-embeddings`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    if (!requireAdmin(req as any, reply)) return;
    const traceId = req.headers["x-correlation-id"] as string;
    try {
      const result = await callInternalAgent("/internal/v1/knia/rebuild-embeddings", req.body ?? {}, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 240000, retryCount: 0 });
      return { result, trace_id: traceId };
    } catch {
      return reply.code(502).send(errorPayload("KNIA_EMBEDDING_FAILED", "KNIA 임베딩 재생성에 실패했습니다.", traceId));
    }
  });

  app.post(`${env.apiPrefix}/admin/knia/import-json`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    if (!requireAdmin(req as any, reply)) return;
    const traceId = req.headers["x-correlation-id"] as string;
    try {
      const result = await callInternalAgent("/internal/v1/knia/import-json", req.body ?? {}, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 600000, retryCount: 0 });
      return { result, trace_id: traceId };
    } catch (err: any) {
      return reply.code(502).send(errorPayload("KNIA_JSON_IMPORT_FAILED", "KNIA JSON 데이터를 가져오지 못했습니다. 파일 경로와 데이터 형식을 확인해 주세요.", traceId));
    }
  });

  app.post(`${env.apiPrefix}/admin/knia/json/rebuild-embeddings`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    if (!requireAdmin(req as any, reply)) return;
    const traceId = req.headers["x-correlation-id"] as string;
    try {
      const result = await callInternalAgent("/internal/v1/knia/json/rebuild-embeddings", req.body ?? {}, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 600000, retryCount: 0 });
      return { result, trace_id: traceId };
    } catch {
      return reply.code(502).send(errorPayload("KNIA_JSON_EMBEDDING_FAILED", "KNIA JSON 임베딩 재생성에 실패했습니다.", traceId));
    }
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

  app.post(`${env.apiPrefix}/admin/cache/invalidate`, async (req, reply) => {
    if (!requireUser(req as any, reply)) return;
    if (!requireAdmin(req as any, reply)) return;
    const traceId = req.headers["x-correlation-id"] as string;
    try {
      const result = await callInternalAgent("/internal/v1/cache/invalidate", req.body ?? { scope: "knia_json" }, traceId, { baseUrl: env.agentUrl, internalToken: env.internalToken, timeoutMs: 60000, retryCount: 0 });
      return { result, trace_id: traceId };
    } catch {
      return reply.code(502).send(errorPayload("CACHE_INVALIDATE_FAILED", "캐시 무효화에 실패했습니다.", traceId));
    }
  });
}
