# LawCompass

단일 서버(2GB RAM) 기준 교통사고 AI 분석 MVP 모노레포.

- Frontend: Vue3 + TypeScript + Vite
- Gateway: Fastify + TypeScript
- Agent: FastAPI + OpenAI API 연동
- Worker: Redis Streams Consumer Group
- DB: PostgreSQL + pgvector
- Cache/Queue: Redis
- Storage: AWS S3(private + presigned)

## 빠른 시작
1. `.env` 값 확인 (`OPENAI_API_KEY`, AWS/S3, DB/Redis)
2. `docker compose --env-file .env up --build`
3. `docker compose exec agent python scripts/ingest_kb.py`
4. 브라우저 `http://localhost` 접속

자세한 운영 절차는 `docs/OPERATIONS.md` 참고.
