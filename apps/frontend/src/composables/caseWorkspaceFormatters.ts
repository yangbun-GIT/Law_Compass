export function prettySize(bytes: number) {
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatDate(iso: string) {
    return new Date(iso).toLocaleString("ko-KR", { dateStyle: "medium", timeStyle: "short" });
}

export function statusLabel(status?: string) {
    const labels: Record<string, string> = {
        draft: "작성 중",
        ready: "분석 가능",
        queued: "대기 중",
        running: "분석 중",
        retrying: "다시 확인 중",
        processing: "영상 확인 중",
        analyzing: "사고 장면 분석 중",
        completed: "완료",
        succeeded: "완료",
        ready_for_analysis: "분석 준비",
        failed: "분석 실패. 다시 시도해 주세요.",
        uploaded: "업로드 완료",
    };

    return status ? labels[status] || status : "상태 없음";
}

export function statusClass(status?: string) {
    if (status === "completed" || status === "ready" || status === "ready_for_analysis" || status === "uploaded") return "ok";
    if (status === "failed") return "fail";
    return "warn";
}
