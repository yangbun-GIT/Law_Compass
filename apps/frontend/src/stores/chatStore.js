import { defineStore } from "pinia";
import { chatApi } from "../api/chat";
import { router } from "../router";
const DRAFT_KEY = "lawcompass:draftCase";
function routeContext(extra = {}) {
    const route = router.currentRoute.value;
    const path = route.path;
    let page = "dashboard";
    if (path.includes("/result"))
        page = "result";
    if (path.includes("/cases/new"))
        page = "new_case";
    if (path.includes("/wizard"))
        page = "upload";
    if (path.includes("/knia/ranking"))
        page = "knia_ranking";
    if (path.includes("/knia/charts"))
        page = "knia_chart";
    return {
        page,
        current_route: path,
        case_id: String(route.params.caseId || extra.case_id || "") || undefined,
        chart_no: String(route.params.chartNo || extra.chart_no || "") || undefined,
        ...extra
    };
}
export const useChatStore = defineStore("chat", {
    state: () => ({
        isOpen: false,
        sessionId: null,
        messages: [],
        suggestions: [],
        draftCase: null,
        kniaMatches: [],
        kniaPrimaryMatch: null,
        context: {},
        isLoading: false,
        unreadCount: 0,
        error: ""
    }),
    actions: {
        async open(context = {}) {
            this.isOpen = true;
            this.unreadCount = 0;
            this.context = routeContext(context);
            if (!this.sessionId) {
                const session = await chatApi.createSession({ context: this.context, case_id: this.context.case_id ?? null });
                this.sessionId = session.session.id;
                this.suggestions = [
                    { label: "블랙박스 영상 올리는 법", action: "send_message", message: "블랙박스 영상 어디서 올려?" },
                    { label: "정차 중 후미추돌 사고 도움", action: "send_message", message: "정차 중 뒤차가 박았어. 어떻게 해야 해?" },
                    { label: "사고 상황 입력 도와줘", action: "send_message", message: "사고 상황 입력 도와줘" },
                    { label: "많이 검색된 사고유형 보기", action: "navigate", target: "/knia/ranking" }
                ];
            }
        },
        close() {
            this.isOpen = false;
        },
        async sendMessage(text) {
            const content = text.trim();
            if (!content || this.isLoading)
                return;
            if (!this.sessionId)
                await this.open(this.context);
            if (!this.sessionId)
                return;
            this.error = "";
            this.isLoading = true;
            this.messages.push({ role: "user", content });
            try {
                const res = await chatApi.sendMessage(this.sessionId, { message: content, context: routeContext(this.context) });
                const assistant = {
                    role: "assistant",
                    content: res.reply,
                    intent: res.intent,
                    suggestions: res.suggestions,
                    draft_case: res.draft_case,
                    knia_matches: res.knia_matches,
                    knia_primary_match: res.knia_primary_match,
                    safety: res.safety
                };
                this.messages.push(assistant);
                this.suggestions = res.suggestions || [];
                this.draftCase = res.draft_case || null;
                this.kniaMatches = res.knia_matches || [];
                this.kniaPrimaryMatch = res.knia_primary_match || null;
                if (!this.isOpen)
                    this.unreadCount += 1;
            }
            catch (err) {
                this.error = err?.message || "AI 사고 도우미 연결에 실패했습니다.";
                this.messages.push({ role: "assistant", content: this.error });
            }
            finally {
                this.isLoading = false;
            }
        },
        async applySuggestion(suggestion) {
            if (suggestion.action === "send_message" || suggestion.action === "open_result_help") {
                await this.sendMessage(suggestion.message || suggestion.label);
                return;
            }
            if (suggestion.action === "navigate" || suggestion.action === "open_upload") {
                if (suggestion.target)
                    await router.push(suggestion.target);
                this.close();
                return;
            }
            if (suggestion.action === "open_external") {
                if (suggestion.target)
                    window.open(suggestion.target, "_blank", "noopener,noreferrer");
                return;
            }
            if (suggestion.action === "apply_case_draft") {
                const draft = (suggestion.payload?.draft_case || suggestion.payload || this.draftCase);
                if (draft)
                    await this.applyDraftCase(draft);
            }
        },
        async applyDraftCase(draftCase) {
            const enriched = { ...draftCase, knia_match: draftCase.knia_match || this.kniaPrimaryMatch || null };
            this.draftCase = enriched;
            localStorage.setItem(DRAFT_KEY, JSON.stringify(enriched));
            await chatApi.applyDraft(enriched).catch(() => null);
            await router.push("/cases/new");
            this.close();
        }
    }
});
