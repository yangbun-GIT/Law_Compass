<template>
  <section class="mobile-demo-page">
    <div class="mobile-demo-hero">
      <p class="eyebrow">LawCompass App Packaging Lab</p>
      <h2>ML Kit 온디바이스 객체 후보 추출 테스트</h2>
      <p>
        이 페이지는 앱 패키징 및 ML Kit 성능 검증용이며, 과실비율을 확정하지 않습니다.
        결과는 서버 Agent 판단을 대체하지 않는 client_pre_observations 초안입니다.
      </p>
    </div>

    <div class="mobile-demo-warning">
      영상에는 얼굴, 번호판, 위치정보가 포함될 수 있습니다. 원본 영상은 이 데모에서 자동 업로드하지 않으며,
      서버 전송 버튼을 누른 경우에도 테스트 검증 endpoint로 관찰값 JSON만 전송합니다.
    </div>

    <div class="mobile-demo-grid">
      <section class="card mobile-demo-panel">
        <h3>영상과 분석 옵션</h3>
        <label>
          영상 파일 선택
          <input type="file" accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm" @change="onFile" />
        </label>

        <video v-if="videoUrl" :src="videoUrl" controls playsinline class="mobile-demo-video"></video>
        <div v-if="videoMetadata" class="mobile-demo-file-meta">
          <span>duration {{ videoMetadata.durationSec.toFixed(2) }}s</span>
          <span>{{ videoMetadata.originalWidth }}x{{ videoMetadata.originalHeight }}</span>
          <span>{{ (videoMetadata.sizeBytes / 1024 / 1024).toFixed(2) }} MB</span>
        </div>

        <div class="mobile-demo-options">
          <label>
            샘플링 FPS
            <input v-model.number="options.samplingFps" type="number" min="0.1" max="10" step="0.1" />
          </label>
          <label>
            최대 프레임 수
            <input v-model.number="options.maxFrames" type="number" min="1" max="120" />
          </label>
          <label>
            confidence threshold
            <input v-model.number="options.confidenceThreshold" type="number" min="0" max="1" step="0.05" />
          </label>
          <label>
            frame resize width
            <input v-model.number="options.resizeWidth" type="number" min="160" max="1920" step="20" />
          </label>
          <label class="toggle-row">
            <input v-model="options.enableTracking" type="checkbox" />
            tracking 사용
          </label>
          <label class="toggle-row">
            <input v-model="options.mockMode" type="checkbox" />
            브라우저 mock fallback 사용
          </label>
        </div>

        <div class="mobile-demo-status" :class="{ unavailable: !pluginStatus.available }">
          <strong>{{ pluginStatus.available ? "Native ML Kit plugin available" : "Native plugin unavailable" }}</strong>
          <span>{{ pluginStatus.reason || "Android Capacitor runtime에서 실제 ML Kit 호출을 시도합니다." }}</span>
        </div>

        <button class="btn" type="button" :disabled="!selectedFile || running || (!pluginStatus.available && !options.mockMode)" @click="runAnalysis">
          {{ running ? "분석 중..." : "ML Kit 분석 실행" }}
        </button>
      </section>

      <section class="card mobile-demo-panel">
        <h3>성능 요약</h3>
        <div class="mobile-demo-summary">
          <div v-for="item in summaryItems" :key="item.label">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
        <VideoFramePreview :frame="firstFrame" :objects="firstDetection?.objects || []" />
      </section>
    </div>

    <section class="card mobile-demo-panel">
      <div class="mobile-demo-actions">
        <h3>객체 후보 테이블</h3>
        <div>
          <button class="btn secondary" type="button" :disabled="!result?.payload" @click="exportJson">client_pre_observations.json 다운로드</button>
          <button class="btn secondary" type="button" :disabled="!result?.payload || sending" @click="sendToGateway">
            {{ sending ? "전송 중..." : "Gateway 테스트 endpoint로 전송" }}
          </button>
          <button class="btn" type="button" :disabled="!canRunVideoOnlyAnalysis || analyzingVideoOnly" @click="runVideoOnlyAnalysis">
            {{ analyzingVideoOnly ? "평가 중..." : "영상-only 분석 가능성 평가 실행" }}
          </button>
        </div>
      </div>
      <div class="mobile-demo-status" :class="{ unavailable: !isAdminDemoUser }">
        <strong>현재 권한: {{ currentRole || "로그인 필요" }}</strong>
        <span>{{ isAdminDemoUser ? "관리자 테스트 endpoint를 호출할 수 있습니다." : "관리자 테스트 로그인 필요: admin 또는 superuser만 영상-only 평가를 실행할 수 있습니다." }}</span>
      </div>
      <p v-if="serverMessage" class="muted">{{ serverMessage }}</p>
      <MlKitResultTable :rows="result?.payload.observations || []" />
    </section>

    <section class="card mobile-demo-panel">
      <h3>영상-only 사고 분석 가능성 평가</h3>
      <div v-if="videoOnlyResult" class="mobile-demo-readiness">
        <div>
          <span>사고상황 이해 가능성</span>
          <strong>{{ videoOnlyResult.analysis_readiness?.can_infer_accident_context ? "후보 생성 가능" : "부족" }}</strong>
        </div>
        <div>
          <span>과실비율 산정 가능성</span>
          <strong>{{ videoOnlyResult.analysis_readiness?.can_estimate_fault_ratio ? "참고 가능" : "needs_review" }}</strong>
        </div>
        <div>
          <span>가능한 대분류 후보</span>
          <strong>{{ videoOnlyResult.candidate_accident_context?.possible_party_type || "불명확" }}</strong>
        </div>
        <div>
          <span>reference_only</span>
          <strong>{{ videoOnlyResult.fault_ratio_result?.presentation_status === "reference_only" ? "예" : "아니오" }}</strong>
        </div>
      </div>
      <div v-if="videoOnlyResult" class="mobile-demo-two-col">
        <div>
          <h4>감지 요약</h4>
          <pre class="mobile-demo-json compact">{{ JSON.stringify(videoOnlyResult.observation_summary, null, 2) }}</pre>
        </div>
        <div>
          <h4>부족한 사실</h4>
          <ul>
            <li v-for="item in videoOnlyResult.candidate_accident_context?.missing_facts || []" :key="item">{{ item }}</li>
          </ul>
        </div>
      </div>
      <p v-else class="muted">ML Kit 분석 결과를 만든 뒤 관리자 권한으로 영상-only 평가를 실행할 수 있습니다. 영상만으로 확정할 수 없는 내용은 needs_review로 표시됩니다.</p>
    </section>

    <section class="card mobile-demo-panel">
      <h3>관찰값 JSON 미리보기</h3>
      <ObservationJsonPreview :payload="result?.payload || null" />
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from "vue";
import MlKitResultTable from "../components/mobile-demo/MlKitResultTable.vue";
import ObservationJsonPreview from "../components/mobile-demo/ObservationJsonPreview.vue";
import VideoFramePreview from "../components/mobile-demo/VideoFramePreview.vue";
import { api, formatApiError } from "../api/client";
import { useSessionStore } from "../stores/session";
import { downloadClientPreObservations, readVideoMetadata, runMlKitDemo, type MlKitDemoOptions, type MlKitDemoRunResult } from "../services/mobileMlkitDemo";
import { getMlKitPluginStatus } from "../plugins/mlkitObjectDetector";

const session = useSessionStore();
const selectedFile = ref<File | null>(null);
const videoUrl = ref("");
const running = ref(false);
const sending = ref(false);
const analyzingVideoOnly = ref(false);
const serverMessage = ref("");
const result = ref<MlKitDemoRunResult | null>(null);
const videoOnlyResult = ref<any>(null);
const videoMetadata = ref<{ durationSec: number; originalWidth: number; originalHeight: number; sizeBytes: number } | null>(null);
const pluginStatus = ref(getMlKitPluginStatus());

const options = reactive<MlKitDemoOptions>({
  samplingFps: 1,
  maxFrames: 24,
  confidenceThreshold: 0.55,
  enableTracking: true,
  resizeWidth: 640,
  mockMode: !pluginStatus.value.available && import.meta.env.VITE_MLKIT_DEMO_MODE === "true",
});

const firstFrame = computed(() => result.value?.sampledFrames?.[0] || null);
const firstDetection = computed(() => result.value?.detections?.[0] || null);
const currentRole = computed(() => String(session.user?.role || ""));
const isAdminDemoUser = computed(() => currentRole.value === "admin" || currentRole.value === "superuser");
const canRunVideoOnlyAnalysis = computed(() => Boolean(result.value?.payload) && isAdminDemoUser.value && !analyzingVideoOnly.value);

const summaryItems = computed(() => {
  const payload = result.value?.payload;
  const performance = payload?.performance;
  return [
    { label: "provider", value: result.value?.provider || pluginStatus.value.provider },
    { label: "provider_version", value: result.value?.providerVersion || pluginStatus.value.providerVersion || "-" },
    { label: "device/platform", value: result.value?.platform || pluginStatus.value.platform },
    { label: "video_duration_sec", value: result.value ? `${result.value.videoDurationSec.toFixed(2)}s` : videoMetadata.value ? `${videoMetadata.value.durationSec.toFixed(2)}s` : "-" },
    { label: "original_width", value: result.value?.originalWidth || videoMetadata.value?.originalWidth || "-" },
    { label: "original_height", value: result.value?.originalHeight || videoMetadata.value?.originalHeight || "-" },
    { label: "sampled_frame_count", value: performance?.sampled_frame_count ?? 0 },
    { label: "processed_frame_count", value: performance?.processed_frame_count ?? 0 },
    { label: "failed_frame_count", value: performance?.failed_frame_count ?? 0 },
    { label: "total_processing_ms", value: Math.round(performance?.total_processing_ms ?? 0) },
    { label: "avg_processing_ms_per_frame", value: (performance?.avg_processing_ms_per_frame ?? 0).toFixed(1) },
    { label: "detected_object_count", value: result.value?.detectedObjectCount ?? 0 },
    { label: "unique_track_count", value: result.value?.uniqueTrackCount ?? 0 },
    { label: "average_confidence", value: `${Math.round((result.value?.averageConfidence ?? 0) * 100)}%` },
    { label: "warnings", value: result.value?.payload.warnings?.length ?? 0 },
  ];
});

async function onFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0] || null;
  selectedFile.value = file;
  result.value = null;
  videoOnlyResult.value = null;
  videoMetadata.value = null;
  serverMessage.value = "";
  if (videoUrl.value) URL.revokeObjectURL(videoUrl.value);
  videoUrl.value = file ? URL.createObjectURL(file) : "";
  if (file) {
    videoMetadata.value = await readVideoMetadata(file).catch(() => null);
  }
}

async function runAnalysis() {
  if (!selectedFile.value) return;
  running.value = true;
  serverMessage.value = "";
  pluginStatus.value = getMlKitPluginStatus();
  try {
    result.value = await runMlKitDemo(selectedFile.value, { ...options });
  } catch (error) {
    serverMessage.value = error instanceof Error ? error.message : "ML Kit 분석 실행에 실패했습니다.";
  } finally {
    running.value = false;
  }
}

function exportJson() {
  if (result.value?.payload) downloadClientPreObservations(result.value.payload);
}

async function sendToGateway() {
  if (!result.value?.payload) return;
  sending.value = true;
  serverMessage.value = "";
  try {
    const response = await api.submitMobileDemoObservations(result.value.payload);
    serverMessage.value = `Gateway 검증 완료: ${response.received_count ?? 0}개 관찰값 수신`;
  } catch (error) {
    serverMessage.value = formatApiError(error, "Gateway 테스트 endpoint 전송에 실패했습니다.");
  } finally {
    sending.value = false;
  }
}

async function runVideoOnlyAnalysis() {
  if (!result.value?.payload) return;
  analyzingVideoOnly.value = true;
  serverMessage.value = "";
  try {
    videoOnlyResult.value = await api.runMobileDemoVideoOnlyAnalysis({
      mode: "video_only_mlkit_demo",
      user_text: "",
      video_metadata: {
        duration_sec: result.value.videoDurationSec,
        original_width: result.value.originalWidth,
        original_height: result.value.originalHeight,
      },
      client_pre_observations: result.value.payload,
    });
    serverMessage.value = "영상-only 분석 가능성 평가가 완료되었습니다.";
  } catch (error) {
    serverMessage.value = formatApiError(error, "영상-only 분석 가능성 평가에 실패했습니다.");
  } finally {
    analyzingVideoOnly.value = false;
  }
}

onBeforeUnmount(() => {
  if (videoUrl.value) URL.revokeObjectURL(videoUrl.value);
});
</script>
