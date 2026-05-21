<template>
  <section class="easy-report">
    <div class="btn-row">
      <button class="btn secondary" @click="loadAll">새로고침</button>
      <RouterLink class="btn secondary" :to="`/cases/${caseId}/result`">결과 크게 보기</RouterLink>
    </div>

    <article v-if="caseData" class="card hero-card">
      <p class="kv">현재 케이스</p>
      <h2>{{ caseData.title }}</h2>
      <p>{{ descriptionText || "사고 설명을 입력해 주세요." }}</p>
    </article>

    <article class="card easy-card">
      <h2>1. 사고 상황 입력</h2>
      <label>사고 설명
        <textarea v-model="descriptionText" rows="5" placeholder="예: 신호대기 중 정차했는데 뒤 차량이 추돌했습니다. 목이 아픕니다." />
      </label>
      <div class="form-grid">
        <label>분석 모드
          <select v-model="analysisMode" @change="applyPreset">
            <option value="quick_summary">빠른 요약</option>
            <option value="rear-end-focused">후미추돌</option>
            <option value="intersection-signal-focused">교차로 신호위반</option>
            <option value="lane-change-focused">차선변경</option>
            <option value="school-zone-focused">어린이보호구역</option>
          </select>
        </label>
        <label>사고 유형
          <select v-model="facts.accident_type">
            <option value="rear_end_collision">후미추돌</option>
            <option value="intersection_collision">교차로 충돌</option>
            <option value="lane_change_collision">차선변경 충돌</option>
            <option value="pedestrian">보행자 사고</option>
          </select>
        </label>
        <label>상대 차량 행동 <input v-model="facts.opponent_behavior" placeholder="예: 뒤에서 추돌" /></label>
        <label>차량 손상 정도 <input v-model="facts.damage_level" placeholder="예: 범퍼 파손" /></label>
      </div>
      <div class="chips">
        <label class="chip"><input type="checkbox" v-model="facts.stopped" /> 정차 중</label>
        <label class="chip"><input type="checkbox" v-model="facts.sudden_brake" /> 급정거</label>
        <label class="chip"><input type="checkbox" v-model="facts.injury" /> 다친 사람 있음</label>
        <label class="chip"><input type="checkbox" v-model="facts.school_zone" /> 어린이보호구역</label>
        <label class="chip"><input type="checkbox" v-model="facts.opponent_signal_violation" /> 상대 신호위반</label>
        <label class="chip"><input type="checkbox" v-model="facts.lane_change" /> 차선변경</label>
      </div>
      <div class="chips">
        <button v-for="kw in keywordPool" :key="kw" class="chip" :class="{ selected: selectedKeywords.includes(kw) }" @click="toggleKeyword(kw)">{{ kw }}</button>
      </div>
      <button class="btn" @click="saveCaseInputs">입력 저장</button>
      <p :class="messageOk ? 'msg-ok' : 'msg-error'">{{ message }}</p>
    </article>

    <article class="card easy-card">
      <h2>2. 영상 업로드</h2>
      <p class="kv">현재는 S3 없이 로컬 업로드로 작동합니다.</p>
      <input type="file" accept="video/*" @change="onFile" />
      <p v-if="file" class="kv">선택 파일: {{ file.name }} ({{ prettySize(file.size) }})</p>
      <div class="btn-row">
        <button class="btn" :disabled="!file || uploading" @click="uploadLocal">로컬 업로드</button>
        <button class="btn secondary" :disabled="!activeUploadId" @click="completeUpload">전처리 시작</button>
        <button class="btn secondary" @click="loadUploads">업로드 목록 갱신</button>
      </div>
      <label>업로드 선택
        <select v-model="selectedUploadId">
          <option value="">선택하세요</option>
          <option v-for="up in uploads" :key="up.id" :value="up.id">{{ up.file_name }} / {{ up.status }}</option>
        </select>
      </label>
      <div class="btn-row">
        <button class="btn secondary" :disabled="!activeUploadId" @click="fetchViewUrl">영상 재생</button>
        <button class="btn secondary" :disabled="!activeUploadId" @click="fetchDownloadUrl">다운로드</button>
      </div>
      <video v-if="viewUrl" controls :src="viewUrl" class="video-preview"></video>
    </article>

    <article class="card easy-card">
      <h2>3. 분석 요청</h2>
      <div class="btn-row">
        <button class="btn" :disabled="analyzing" @click="analyzeText">텍스트 분석</button>
        <button class="btn secondary" :disabled="!activeUploadId || analyzing" @click="analyzeVideo">영상 분석 작업 등록</button>
        <button class="btn secondary" @click="loadJobs">작업 조회</button>
        <button class="btn secondary" @click="loadReport">결과 새로고침</button>
      </div>
      <ul class="list-reset job-list" v-if="jobs.length">
        <li v-for="job in jobs" :key="job.id"><strong>{{ job.type }}</strong><p class="kv">{{ job.status }} / attempts: {{ job.attempts ?? job.attempt }}</p></li>
      </ul>
    </article>

    <EasyReportView v-if="report" :report="report" />
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import EasyReportView from "../components/easy/EasyReportView.vue";
import { api, type AccidentFacts, type UploadItem } from "../api/client";
const caseId = useRoute().params.caseId as string;
const caseData = ref<any>(null);
const descriptionText = ref("");
const facts = ref<AccidentFacts>({ accident_type: "rear_end_collision", stopped: true, injury: null });
const analysisMode = ref("quick_summary");
const selectedKeywords = ref<string[]>(["후미추돌", "안전거리", "블랙박스", "과실비율"]);
const file = ref<File | null>(null);
const uploads = ref<UploadItem[]>([]);
const selectedUploadId = ref("");
const viewUrl = ref("");
const jobs = ref<any[]>([]);
const report = ref<any>(null);
const message = ref("");
const messageOk = ref(true);
const uploading = ref(false);
const analyzing = ref(false);
let pollTimer: number | null = null;
const activeUploadId = computed(() => selectedUploadId.value);
const keywordPool = ["후미추돌", "안전거리", "신호위반", "교차로", "차선변경", "방향지시등", "횡단보도", "보행자", "어린이보호구역", "민식이법", "대인접수", "진단서"];
function prettySize(bytes: number) { return `${(bytes / (1024 * 1024)).toFixed(2)} MB`; }
function onFile(e: Event) { file.value = (e.target as HTMLInputElement).files?.[0] || null; }
function toggleKeyword(kw: string) { selectedKeywords.value = selectedKeywords.value.includes(kw) ? selectedKeywords.value.filter((x) => x !== kw) : [...selectedKeywords.value, kw]; }
function applyPreset() {
  if (analysisMode.value === "rear-end-focused") { facts.value = { ...facts.value, accident_type: "rear_end_collision", stopped: true }; selectedKeywords.value = ["후미추돌", "안전거리", "대인접수", "진단서"]; }
  if (analysisMode.value === "lane-change-focused") { facts.value = { ...facts.value, accident_type: "lane_change_collision", lane_change: true }; selectedKeywords.value = ["차선변경", "방향지시등", "측면충돌"]; }
  if (analysisMode.value === "intersection-signal-focused") { facts.value = { ...facts.value, accident_type: "intersection_collision", intersection: true, opponent_signal_violation: true }; selectedKeywords.value = ["신호위반", "교차로", "과실비율"]; }
  if (analysisMode.value === "school-zone-focused") { facts.value = { ...facts.value, accident_type: "pedestrian", school_zone: true, victim_is_child: true, injury: true }; selectedKeywords.value = ["민식이법", "어린이보호구역", "보행자", "형사책임"]; }
}
function payload() { return { description_text: descriptionText.value, structured_facts: facts.value, selected_keywords: selectedKeywords.value, analysis_mode: analysisMode.value }; }
async function loadCase() { const data = await api.getCase(caseId); caseData.value = data.case; descriptionText.value = data.case.description_text || ""; facts.value = { ...facts.value, ...(data.case.structured_facts || {}) }; selectedKeywords.value = data.case.selected_keywords?.length ? data.case.selected_keywords : selectedKeywords.value; analysisMode.value = data.case.analysis_mode || analysisMode.value; }
async function saveCaseInputs() { try { const data = await api.updateCase(caseId, { description_text: descriptionText.value, structured_facts: facts.value, selected_keywords: selectedKeywords.value, analysis_mode: analysisMode.value }); caseData.value = data.case; message.value = "입력값을 저장했습니다."; messageOk.value = true; } catch (e: any) { message.value = e.message; messageOk.value = false; } }
async function loadUploads() { const data = await api.getCaseUploads(caseId); uploads.value = data.items || []; if (!selectedUploadId.value && uploads.value.length) selectedUploadId.value = uploads.value[0].id; }
async function uploadLocal() { if (!file.value) return; uploading.value = true; try { await saveCaseInputs(); const data = await api.localUpload(caseId, file.value); selectedUploadId.value = data.upload_id; message.value = "로컬 업로드가 완료되었습니다."; await loadUploads(); } catch (e: any) { message.value = e.message; messageOk.value = false; } finally { uploading.value = false; } }
async function completeUpload() { try { const data = await api.completeUpload(activeUploadId.value); message.value = `전처리 작업 등록: ${data.job_id}`; await loadJobs(); startPollingJobs(); } catch (e: any) { message.value = e.message; messageOk.value = false; } }
async function fetchViewUrl() { viewUrl.value = (await api.getViewUrl(activeUploadId.value)).view_url; }
async function fetchDownloadUrl() { window.open((await api.getDownloadUrl(activeUploadId.value)).download_url, "_blank"); }
async function analyzeText() { analyzing.value = true; try { await api.analyzeText(caseId, payload()); await loadReport(); } catch (e: any) { message.value = e.message; messageOk.value = false; } finally { analyzing.value = false; } }
async function analyzeVideo() { analyzing.value = true; try { await saveCaseInputs(); const data = await api.analyzeVideo(caseId, { upload_id: activeUploadId.value, ...payload() }); message.value = `영상 분석 작업 등록: ${data.job_id}`; await loadJobs(); startPollingJobs(); } catch (e: any) { message.value = e.message; messageOk.value = false; } finally { analyzing.value = false; } }
async function loadJobs() { jobs.value = (await api.getJobs(caseId)).items || []; }
async function loadReport() { try { report.value = await api.getEasyReport(caseId); } catch { report.value = null; } }
async function loadAll() { await loadCase(); await loadUploads(); await loadJobs(); await loadReport(); }
function startPollingJobs() { stopPolling(); pollTimer = window.setInterval(async () => { await loadJobs(); if (!jobs.value.some((j) => ["queued", "running", "retrying"].includes(j.status))) { stopPolling(); await loadUploads(); await loadReport(); } }, 2500); }
function stopPolling() { if (pollTimer !== null) window.clearInterval(pollTimer); pollTimer = null; }
onMounted(loadAll); onBeforeUnmount(stopPolling);
</script>
