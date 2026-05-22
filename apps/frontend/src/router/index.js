import { createRouter, createWebHistory } from "vue-router";
import LoginView from "../views/LoginView.vue";
import SignupView from "../views/SignupView.vue";
import DashboardView from "../views/DashboardView.vue";
import CaseDetailView from "../views/CaseDetailView.vue";
import CaseCreateView from "../views/CaseCreateView.vue";
import AccidentWizardView from "../views/AccidentWizardView.vue";
import CaseResultView from "../views/CaseResultView.vue";
import AgentLabView from "../views/AgentLabView.vue";
import EvidenceDetailView from "../views/EvidenceDetailView.vue";
import KniaRankingView from "../views/KniaRankingView.vue";
import KniaChartView from "../views/KniaChartView.vue";
import { pinia } from "../stores";
import { useSessionStore } from "../stores/session";
export const router = createRouter({
    history: createWebHistory(),
    routes: [
        { path: "/", component: DashboardView, meta: { requiresAuth: true } },
        { path: "/login", component: LoginView },
        { path: "/signup", component: SignupView },
        { path: "/cases/new", component: CaseCreateView, meta: { requiresAuth: true } },
        { path: "/cases/:caseId", component: CaseDetailView, meta: { requiresAuth: true } },
        { path: "/cases/:caseId/wizard", component: AccidentWizardView, meta: { requiresAuth: true } },
        { path: "/cases/:caseId/result", component: CaseResultView, meta: { requiresAuth: true } },
        { path: "/cases/:caseId/agents", component: AgentLabView, meta: { requiresAuth: true } },
        { path: "/evidence/:chunkId", component: EvidenceDetailView, meta: { requiresAuth: true } },
        { path: "/knia/ranking", component: KniaRankingView, meta: { requiresAuth: true } },
        { path: "/knia/myaccident", redirect: "/knia/ranking", meta: { requiresAuth: true } },
        { path: "/knia/myaccident/:myaccidentNo", redirect: "/knia/ranking", meta: { requiresAuth: true } },
        { path: "/knia/charts/:chartNo", component: KniaChartView, meta: { requiresAuth: true } }
    ]
});
router.beforeEach(async (to) => {
    const session = useSessionStore(pinia);
    await session.bootstrap();
    if (to.meta.requiresAuth && !session.user) {
        return { path: "/login", query: { redirect: to.fullPath } };
    }
    if ((to.path === "/login" || to.path === "/signup") && session.user) {
        return "/";
    }
    return true;
});
