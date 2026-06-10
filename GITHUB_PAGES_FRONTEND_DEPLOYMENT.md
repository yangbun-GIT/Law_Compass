# GitHub Pages 프론트엔드 배포 가이드

이 문서는 LawCompass의 Vue 프론트엔드만 GitHub Pages에 배포하는 절차를 정리한다. Gateway, Agent, Worker, PostgreSQL, Redis는 GitHub Pages에서 실행할 수 없으므로 OCI Free Tier 또는 별도 서버의 Docker Compose 배포가 필요하다.

## 배포 구조

| 구분 | 배포 위치 | 역할 |
| --- | --- | --- |
| Frontend | GitHub Pages | Vue 정적 파일 제공 |
| Gateway | OCI 또는 별도 서버 | 인증, 업로드, 케이스, 분석 API |
| Agent | OCI 또는 별도 서버 | 사고 분석, KNIA/RAG, 질문 생성 |
| Worker | OCI 또는 별도 서버 | 영상 전처리와 분석 job 처리 |
| PostgreSQL/Redis | OCI 또는 별도 서버 | 업무 데이터, KB/RAG, queue/cache |

## 사전 준비

1. GitHub 저장소의 `Settings > Pages`에서 `Build and deployment > Source`를 `GitHub Actions`로 선택한다.
2. 백엔드를 먼저 배포한 경우 `Settings > Secrets and variables > Actions > Variables`에 아래 값을 추가한다.

```text
VITE_API_BASE_URL=https://<your-domain-or-public-ip>/api/v1
```

백엔드가 아직 없다면 이 값을 비워둘 수 있다. 이 경우 GitHub Pages 화면은 열리지만 로그인, 업로드, 분석 API는 동작하지 않는다.

별도 OCI/Gateway 도메인을 연결하는 경우 Gateway `.env`에도 아래 값을 맞춘다.

```text
CORS_ORIGINS=https://yangbun-git.github.io
COOKIE_SAME_SITE=none
```

`COOKIE_SAME_SITE=none`은 HTTPS 운영에서만 사용한다. 같은 도메인에서 Caddy가 `/api/*`를 Gateway로 reverse proxy하는 기본 운영은 `COOKIE_SAME_SITE=lax`가 더 단순하고 안정적이다.

## 자동 배포

`main` 브랜치에 아래 경로가 push되면 `.github/workflows/pages.yml`이 실행된다.

- `apps/frontend/**`
- `.github/workflows/pages.yml`

workflow는 다음 순서로 동작한다.

1. `apps/frontend` 의존성을 `npm ci`로 설치한다.
2. `VITE_BASE_PATH=/Law_Compass/`로 Vite 정적 파일을 빌드한다.
3. SPA 새로고침 fallback을 위해 `dist/index.html`을 `dist/404.html`로 복사한다.
4. `actions/upload-pages-artifact`로 `apps/frontend/dist`를 업로드한다.
5. `actions/deploy-pages`로 GitHub Pages에 배포한다.

## 배포 URL

기본 프로젝트 Pages URL은 아래 형식이다.

```text
https://yangbun-git.github.io/Law_Compass/
```

배포 후 반영까지 몇 분 정도 걸릴 수 있다.

## 주의사항

- GitHub Pages는 정적 호스팅이므로 서버 API, DB, Redis, 파일 업로드 저장소를 제공하지 않는다.
- `VITE_API_BASE_URL`은 실제 Gateway의 공개 HTTPS 주소를 사용해야 한다.
- 쿠키 기반 로그인은 프론트와 API 도메인이 다르면 브라우저 정책 영향을 받는다. 실제 운영은 같은 도메인에서 Caddy가 `/api/*`를 Gateway로 reverse proxy하는 OCI 배포가 가장 안정적이다.
- `.env`, 실제 secret, 원본 영상, storage/log/cache 산출물은 GitHub에 올리지 않는다.
