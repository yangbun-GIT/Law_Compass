# LawCompass

단일 서버(2GB RAM) 기준 교통사고 AI 분석 MVP 모노레포.

- Frontend: Vue3 + TypeScript + Vite
- Gateway: Fastify + TypeScript
- Agent: FastAPI + OpenAI API 연동
- Worker: Redis Streams Consumer Group
- DB: PostgreSQL + pgvector
- Cache/Queue: Redis
- Storage: StorageAdapter 기반 `local`, 비활성 legacy `s3`, `nas_sftp` 드라이버. NAS는 앱/DB 실행 위치가 아니라 영상, 프레임, 리포트, DB 백업 파일 저장소로만 사용한다.

## 빠른 시작
1. `env.example`을 참고해 `.env` 값을 준비 (`OPENAI_API_KEY`, DB/Redis, `STORAGE_DRIVER` 및 저장소 기본값)
2. `docker compose --env-file .env up --build`
3. `docker compose exec agent python scripts/ingest_kb.py`
4. 브라우저 `http://localhost` 접속

자세한 운영 절차는 `docs/OPERATIONS.md` 참고.
