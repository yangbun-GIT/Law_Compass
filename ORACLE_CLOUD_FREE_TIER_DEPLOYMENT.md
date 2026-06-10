# LawCompass Oracle Cloud Free Tier 운영 가이드

작성일: 2026-06-11
대상: Oracle Cloud Infrastructure, 이하 OCI, Always Free VM 한 대에서 LawCompass MVP를 운영하려는 배포자
범위: 현재 저장소의 `compose.yaml`, `compose.prod.yaml`, `infra/caddy/Caddyfile`, `env.oci.example`, `scripts/oci/*` 기준 운영 절차

이 문서는 LawCompass를 OCI Free Tier에서 최대한 안전하게 실행하기 위한 실무 절차다. 실제 API key, JWT secret, DB password, 내부 토큰, SSH private key, 사용자 사고 영상 원본은 이 문서나 Git에 절대 기록하지 않는다.

## 1. 결론

LawCompass 전체 스택을 OCI Free Tier에서 운영하려면 **VM.Standard.A1.Flex 4 OCPU / 24 GB RAM 단일 VM** 구성이 가장 현실적이다.

| 선택지 | 판단 |
| --- | --- |
| VM.Standard.A1.Flex 4 OCPU / 24 GB | 권장. Frontend, Gateway, Agent, Worker, PostgreSQL/pgvector, Redis, Caddy를 한 VM에서 운영 가능하다. |
| VM.Standard.E2.1.Micro 1 GB RAM | 비권장. PostgreSQL + Redis + Python Agent + Worker + Node build/runtime을 함께 올리기에는 메모리가 부족하다. |
| 여러 Free Tier VM으로 분리 | 대회/OSS MVP 운영에는 과하다. 네트워크, 인증, 백업, 장애 지점이 늘어난다. |
| OCI Autonomous Database로 PostgreSQL 대체 | 현재 프로젝트는 PostgreSQL + pgvector 전제라 바로 대체하지 않는다. |
| Object Storage를 영상 원본 저장소로 사용 | 현재 S3 provider가 미구현 상태라 기본 운영은 로컬 볼륨이다. Object Storage 전환은 별도 기능 작업이다. |

OCI 공식 문서 기준으로 Always Free는 홈 리전에서 Ampere A1 Compute 3,000 OCPU hours와 18,000 GB hours/month를 제공하며, 이는 Always Free 계정 기준 4 OCPU와 24 GB 메모리에 해당한다. Block Volume은 총 200 GB Always Free 한도가 있다. 단, Always Free 인스턴스는 일정 기간 낮은 CPU, 네트워크, 메모리 사용률이면 회수 대상이 될 수 있으므로 모니터링과 백업이 필요하다.

## 2. 현재 LawCompass 배포 구조

현재 `compose.yaml`은 다음 컨테이너를 실행한다.

```text
Internet
  -> OCI public IP / domain
  -> edge(Caddy: 80/443)
  -> frontend(Vue preview: 5173, internal)
  -> gateway(Fastify: 3000, internal)
  -> agent(FastAPI: 8000, internal)
  -> worker(Redis Streams consumer, internal)
  -> postgres(pgvector: 5432, internal)
  -> redis(6379, internal)
```

중요한 네트워크 경계:

- 외부에 열 포트는 `22`, `80`, `443`만 둔다.
- `3000`, `5173`, `8000`, `5432`, `6379`는 OCI Security List/NSG와 host firewall에서 열지 않는다.
- Docker 내부에서는 `app_net`이 internal network로 잡혀 있고, Caddy `edge`만 public network에 연결된다.

중요한 compose 실행 규칙:

- 이 저장소에는 `compose.override.yaml`이 있다.
- 서버 운영에서 `docker compose up`만 실행하면 개발용 override가 자동 적용될 수 있다.
- 운영에서는 반드시 아래처럼 파일을 명시한다.

```bash
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml up -d --build
```

반복 운영에서는 같은 기준을 감싼 스크립트를 사용할 수 있다.

```bash
bash scripts/oci/deploy.sh
```

## 3. OCI Free Tier 리소스 설계

### 3.1 권장 VM

| 항목 | 권장값 |
| --- | --- |
| Image | Ubuntu 24.04 LTS 또는 Ubuntu 22.04 LTS, Always Free Eligible |
| Shape | `VM.Standard.A1.Flex` |
| OCPU | 4 |
| Memory | 24 GB |
| Boot volume | 100~150 GB 권장, Free Tier 총 Block Volume 200 GB 한도 안에서 선택 |
| Public IPv4 | 할당 |
| SSH | key pair only, password login 금지 |

왜 A1 4 OCPU / 24 GB인가:

- PostgreSQL + pgvector는 메모리와 디스크 I/O가 필요하다.
- Worker는 ffmpeg로 영상 전처리를 한다.
- Agent는 FastAPI/Python 의존성과 RAG 검색을 사용한다.
- Gateway/Frontend는 Node 기반 build/runtime을 사용한다.
- 1 GB Micro VM은 전체 서비스를 장시간 안정적으로 유지하기 어렵다.

### 3.2 Free Tier에서 꺼두는 기능

OCI 비용과 OpenAI 비용은 별개다. Free Tier VM에서 돌아가더라도 OpenAI API 호출은 별도 비용이 발생할 수 있다.

기본 운영 `.env` 권장값:

```env
ENABLE_OPENAI_ANALYSTS=0
ENABLE_OPENAI_FRAME_ANALYSIS=0
ENABLE_YOLO_FRAME_ANALYSIS=0
WORKER_CONCURRENCY=1
MAX_UPLOAD_MB=200
```

실제 영상 프레임 분석을 검증할 때만 아래를 켠다.

```env
ENABLE_OPENAI_FRAME_ANALYSIS=1
OPENAI_API_KEY=<server-local-only>
```

## 4. OCI 콘솔에서 인프라 만들기

### 4.1 홈 리전 확인

Always Free Compute와 Block Volume은 홈 리전 기준 제약을 받는다. OCI 가입 시 선택한 홈 리전에서 VM을 만든다.

### 4.2 VCN/Subnet

간단한 MVP 운영은 다음 구성이면 충분하다.

| 항목 | 값 |
| --- | --- |
| VCN | 새 VCN 1개 |
| Subnet | Public Subnet 1개 |
| IPv4 CIDR 예시 | `10.0.0.0/16`, subnet `10.0.0.0/24` |
| Public IPv4 | VM에 할당 |
| Internet Gateway | 사용 |

### 4.3 Security List 또는 NSG Ingress

| Source | Protocol | Port | 용도 |
| --- | --- | --- | --- |
| 내 관리 IP `/32` | TCP | 22 | SSH |
| `0.0.0.0/0` | TCP | 80 | HTTP, Caddy, 인증서 발급 challenge |
| `0.0.0.0/0` | TCP | 443 | HTTPS |

열지 말아야 할 포트:

```text
3000, 5173, 8000, 5432, 6379
```

OCI Ubuntu 이미지는 VCN 보안 규칙과 VM 내부 firewall을 모두 봐야 한다. OCI 공식 블로그도 HTTP/HTTPS 요청이 성공하려면 Security List/NSG와 host firewall 양쪽에서 포트를 열어야 한다고 안내한다.

### 4.4 Compute instance 생성

1. Compute > Instances > Create instance.
2. Image는 Ubuntu 24.04 LTS 또는 22.04 LTS의 Always Free Eligible 이미지를 선택한다.
3. Shape는 `VM.Standard.A1.Flex`.
4. OCPU 4, Memory 24 GB.
5. Boot volume은 100~150 GB 권장.
6. SSH public key를 등록한다.
7. Public IPv4를 할당한다.
8. 생성 후 public IP를 기록한다.

`Out of host capacity`가 나오면 같은 리전의 다른 availability domain을 시도하거나 시간을 두고 재시도한다. 이 오류는 Free Tier A1 자원 부족 상황에서 흔하다.

## 5. DNS와 HTTPS

도메인이 있으면 DNS에서 A record를 설정한다.

```text
lawcompass.example.com -> OCI public IPv4
```

현재 저장소의 `infra/caddy/Caddyfile`은 `LAWCOMPASS_SITE_ADDRESS` 환경변수를 읽는다. 기본값은 `:80`이므로 IP만으로 HTTP 테스트할 때는 그대로 둘 수 있다. 실제 도메인 HTTPS 운영은 `.env`에서 `LAWCOMPASS_SITE_ADDRESS`를 도메인으로 바꾼다.

도메인 운영 `.env` 예시:

```env
LAWCOMPASS_SITE_ADDRESS=lawcompass.example.com
CADDY_ACME_EMAIL=admin@example.com
```

Caddyfile의 핵심 형태:

```caddyfile
{
  email {$CADDY_ACME_EMAIL:admin@example.com}
}

{$LAWCOMPASS_SITE_ADDRESS::80} {
  encode zstd gzip

  @health path /health /ready
  reverse_proxy @health gateway:3000

  @api path /api/* /health /ready
  reverse_proxy @api gateway:3000

  reverse_proxy frontend:5173

  header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains"
    X-Frame-Options "DENY"
    X-Content-Type-Options "nosniff"
    Referrer-Policy "strict-origin-when-cross-origin"
    Content-Security-Policy "default-src 'self'; connect-src 'self' https: http:; img-src 'self' data: blob:; media-src 'self' https: blob:; script-src 'self'; style-src 'self' 'unsafe-inline'"
    Permissions-Policy "camera=(), microphone=(), geolocation=()"
  }
}
```

Caddy는 도메인이 올바르게 VM으로 향하고 80/443 포트가 열려 있으면 인증서를 자동 발급/갱신한다. 도메인 없이 public IP만 쓰면 자동 공개 TLS 인증서는 기대하지 않는다.

## 6. 서버 초기 설정

아래 명령은 Ubuntu 기준이다.

```bash
ssh ubuntu@OCI_PUBLIC_IP

sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y ca-certificates curl gnupg git ufw htop jq unzip
```

### 6.1 Host firewall

OCI Security List/NSG와 별도로 VM 내부 firewall도 맞춘다.

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status verbose
```

### 6.2 Docker Engine 설치

Docker 공식 Ubuntu apt repository 방식으로 설치한다.

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

그 다음 SSH를 끊었다가 다시 접속한다.

```bash
docker version
docker compose version
```

## 7. LawCompass 배포

### 7.1 코드 받기

```bash
sudo mkdir -p /opt/lawcompass
sudo chown "$USER:$USER" /opt/lawcompass
cd /opt/lawcompass

git clone https://github.com/yangbun-GIT/Law_Compass.git .
git status --short --branch
```

### 7.2 운영 디렉터리 준비

```bash
mkdir -p storage logs/gateway logs/agent logs/worker backups
chmod 700 storage logs backups
```

`storage/`, `logs/`, `backups/`, `.env`는 Git에 올리지 않는다.

### 7.3 `.env` 만들기

```bash
cp env.oci.example .env
chmod 600 .env
```

필수로 바꿀 값:

```env
NODE_ENV=production
APP_NAME=LawCompass

POSTGRES_USER=law
POSTGRES_PASSWORD=<generate-on-server>
POSTGRES_DB=lawcompass
DATABASE_URL=postgresql://law:<POSTGRES_PASSWORD>@postgres:5432/lawcompass

JWT_ACCESS_SECRET=<generate-on-server>
JWT_REFRESH_SECRET=<generate-on-server>
INTERNAL_SERVICE_TOKEN=<generate-on-server>

REDIS_URL=redis://redis:6379
VITE_API_BASE_URL=/api/v1

STORAGE_PROVIDER=local
STORAGE_DRIVER=local
LOCAL_STORAGE_ROOT=/app/storage
LOCAL_VIDEO_CACHE_DIR=/app/storage/cache
MAX_UPLOAD_MB=200

ENABLE_OPENAI_ANALYSTS=0
ENABLE_OPENAI_FRAME_ANALYSIS=0
ENABLE_YOLO_FRAME_ANALYSIS=0
OPENAI_API_KEY=<empty-by-default>

KNIA_BASE_URL=https://accident.knia.or.kr
KNIA_REQUEST_DELAY_MS=500
KNIA_TIMEOUT_SEC=15
KNIA_COLLECT_MAX_CHARTS=50
KNIA_FAULT_RATIO_JSON_PATH=/app/project_scripts/knia_fault_ratio/knia_fault_ratio_2023_06.codex_review.json
```

랜덤 값 생성 예시:

```bash
openssl rand -hex 32
openssl rand -base64 32
```

주의:

- OCI 단일 VM 기본 운영은 `env.oci.example`을 사용한다.
- 기존 `env.example`에는 NAS 예시가 남아 있으므로 OCI 서버에서 그대로 복사하지 않는다.
- `.env`의 실제 값은 터미널 출력, 문서, 커밋, 스크린샷에 남기지 않는다.
- OpenAI key를 넣지 않아도 deterministic fallback과 구조화 KNIA JSON 기반 기능은 일부 동작한다.

### 7.4 권장 배포 스크립트

반복 운영에서는 아래 스크립트를 권장한다. 이 스크립트는 운영 디렉터리를 만들고, `STORAGE_DRIVER=local`을 확인하고, `compose.yaml + compose.prod.yaml` 조합만 사용해 build/up/migration/KNIA import/health check를 순서대로 실행한다.

```bash
cd /opt/lawcompass
bash scripts/oci/deploy.sh
```

선택 옵션:

```bash
SKIP_BUILD=1 bash scripts/oci/deploy.sh
RUN_MIGRATIONS=0 bash scripts/oci/deploy.sh
IMPORT_KNIA=0 bash scripts/oci/deploy.sh
LAWCOMPASS_ENV_FILE=.env bash scripts/oci/deploy.sh
```

### 7.5 수동 이미지 build와 기동

스크립트 대신 직접 실행할 때도 반드시 override를 제외하고 prod compose를 명시한다.

```bash
cd /opt/lawcompass

docker compose --env-file .env -f compose.yaml -f compose.prod.yaml build
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml up -d
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml ps
```

로그 확인:

```bash
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml logs -f --tail=100 edge gateway agent worker
```

### 7.6 DB migration

새 `postgres_data` 볼륨으로 처음 시작하면 `infra/postgres/migrations`가 `/docker-entrypoint-initdb.d`로 들어가 초기 schema가 적용된다.

기존 DB 볼륨에 새 migration을 반영할 때는 `db-migrate` profile을 실행한다.

```bash
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml --profile migrate run --rm db-migrate
```

### 7.7 KNIA/법률 데이터 적재

기본 KB seed:

```bash
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml exec agent \
  python scripts/ingest_kb.py
```

2023.6 KNIA 구조화 JSON import:

```bash
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml exec agent \
  python scripts/import_knia_fault_ratio_json.py \
  --path /app/project_scripts/knia_fault_ratio/knia_fault_ratio_2023_06.codex_review.json \
  --rebuild-embeddings
```

외부 법령/공공 API 적재는 `LAW_API_OC`, `DATA_GO_SERVICE_KEY` 같은 별도 키가 있을 때만 실행한다.

```bash
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml exec agent \
  python scripts/ingest_legal_apis.py
```

## 8. 헬스체크와 운영 확인

서버 내부:

```bash
curl -i http://localhost/health
curl -i http://localhost/ready
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml ps
```

외부 PC:

```bash
curl -i http://OCI_PUBLIC_IP/health
curl -i http://OCI_PUBLIC_IP/ready
curl -i https://lawcompass.example.com/health
```

브라우저:

```text
http://OCI_PUBLIC_IP
https://lawcompass.example.com
```

정상 상태:

- `edge`, `frontend`, `gateway`, `agent`, `worker`, `postgres`, `redis`가 running 또는 healthy.
- `/health`가 200 응답.
- Gateway 로그에 DB 연결 오류가 없어야 한다.
- Agent 로그에 KNIA JSON missing이 반복되면 import 경로 또는 `KNIA_FAULT_RATIO_JSON_PATH`를 확인한다.

## 9. 업데이트 절차

1. 원격 변경 확인.

```bash
cd /opt/lawcompass
git fetch origin
git status --short --branch
git log --oneline --decorate -5
```

2. 현재 백업.

```bash
mkdir -p backups
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml exec -T postgres \
  sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  | gzip > "backups/lawcompass_$(date +%F_%H%M).sql.gz"
```

3. 코드 업데이트.

```bash
git pull --ff-only origin main
```

4. migration과 재기동.

```bash
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml --profile migrate run --rm db-migrate
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml build
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml up -d
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml ps
```

5. 헬스체크.

```bash
curl -i http://localhost/health
curl -i http://localhost/ready
```

## 10. 백업과 복구

### 10.1 백업 대상

| 대상 | 위치 | 이유 |
| --- | --- | --- |
| PostgreSQL | Docker volume `postgres_data` | 사용자, 케이스, 분석 결과, KNIA/RAG DB |
| Redis | Docker volume `redis_data` | queue/cache. 영구 중요도는 낮지만 장애 분석에 필요할 수 있음 |
| 업로드/프레임 | `./storage` | 사고 영상 원본, 캐시, 추출 프레임 |
| Caddy 인증서 | Docker volume `caddy_data`, `caddy_config` | HTTPS 인증서/설정 캐시 |
| `.env` | 서버 로컬만 | secret. Git에 올리지 않음 |

### 10.2 DB 백업

권장 스크립트:

```bash
bash scripts/oci/backup_postgres.sh
```

수동 실행:

```bash
mkdir -p backups
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml exec -T postgres \
  sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  | gzip > "backups/lawcompass_$(date +%F_%H%M).sql.gz"
```

### 10.3 storage 백업

```bash
tar -czf "backups/lawcompass_storage_$(date +%F_%H%M).tar.gz" storage
```

### 10.4 원격 백업 권장

OCI Always Free VM 또는 volume이 사라지는 상황에 대비해 백업 파일은 주기적으로 로컬 PC, NAS, 또는 별도 안전한 저장소로 내려받는다.

```bash
scp ubuntu@OCI_PUBLIC_IP:/opt/lawcompass/backups/lawcompass_YYYY-MM-DD_HHMM.sql.gz .
```

## 11. 리소스 운영 기준

### 11.1 메모리

확인 명령:

```bash
free -h
docker stats
```

권장:

- `WORKER_CONCURRENCY=1`.
- OpenAI/Yolo frame analysis는 필요할 때만 켠다.
- PostgreSQL은 현재 `shared_buffers=256MB`, `work_mem=8MB`, `max_connections=80`으로 비교적 보수적이다.
- 메모리 부족이 나면 먼저 Worker와 영상 분석 옵션을 줄인다.

### 11.2 디스크

확인 명령:

```bash
df -h
du -sh storage logs backups
docker system df
```

정리 명령:

```bash
docker image prune -f
docker builder prune -f
find logs -type f -name "*.log" -mtime +14 -delete
```

주의:

- `docker volume prune`은 사용 중이지 않은 volume을 삭제하므로 운영 DB volume을 날리지 않게 조심한다.
- `storage/`는 사고 영상과 프레임이 쌓이므로 주기적 보존 정책이 필요하다.

### 11.3 Idle reclaim 대비

OCI Always Free 문서는 낮은 CPU, 네트워크, 메모리 사용률이 일정 기간 지속되면 idle instance가 회수될 수 있다고 안내한다. 이것을 피하려고 의미 없는 부하를 만드는 방식은 권장하지 않는다. 대신 다음을 지킨다.

- DB와 storage 백업을 자동화한다.
- OCI Monitoring에서 instance 상태 알림을 켠다.
- 서비스가 실제로 쓰이지 않는 장기 휴면 기간에는 백업 후 재생성 가능성을 받아들인다.
- 중요한 시연 전에는 최소 하루 전 접속/헬스체크/백업을 확인한다.

## 12. 보안 체크리스트

필수:

- SSH 22번은 내 관리 IP로 제한한다.
- `.env`는 `chmod 600 .env`.
- `JWT_ACCESS_SECRET`, `JWT_REFRESH_SECRET`, `INTERNAL_SERVICE_TOKEN`, `POSTGRES_PASSWORD`는 기본값을 쓰지 않는다.
- public ingress는 80/443만 둔다.
- DB/Redis/Gateway/Agent/Frontend 내부 포트는 외부에 열지 않는다.
- 원본 사고 영상은 public web root에 직접 두지 않는다.
- `.env`, `storage/`, `logs/`, `backups/`, 원본 영상은 Git에 올리지 않는다.

권장:

- OCI 계정 MFA를 켠다.
- SSH password login을 끈다.
- 관리자 IP가 자주 바뀌면 Bastion 또는 VPN을 검토한다.
- Caddy HTTPS 도메인 운영 시 DNS가 올바른 VM public IP로 향하는지 먼저 확인한다.

## 13. 장애 대응

### 13.1 80/443 접속이 안 됨

확인 순서:

```bash
sudo ufw status verbose
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml ps edge
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml logs edge --tail=100
curl -i http://localhost/health
```

그리고 OCI Console에서 Security List/NSG ingress 80/443이 열려 있는지 확인한다.

### 13.2 `/health`는 되는데 화면이 안 뜸

```bash
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml ps frontend gateway
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml logs frontend gateway --tail=100
```

`compose.override.yaml`이 섞였는지 확인한다.

```bash
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml config | head -80
```

### 13.3 DB 연결 오류

```bash
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml ps postgres
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml logs postgres --tail=100
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml exec postgres pg_isready -U law -d lawcompass
```

`.env`의 `POSTGRES_PASSWORD`와 `DATABASE_URL`의 password가 같은지 확인한다.

### 13.4 KNIA 기준이 안 나옴

```bash
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml exec agent \
  python scripts/import_knia_fault_ratio_json.py \
  --path /app/project_scripts/knia_fault_ratio/knia_fault_ratio_2023_06.codex_review.json \
  --rebuild-embeddings
```

`scripts/knia_fault_ratio/knia_fault_ratio_2023_06.codex_review.json` 파일이 저장소에 있는지 확인한다.

### 13.5 영상 업로드가 느리거나 실패

- `MAX_UPLOAD_MB`를 줄인다.
- `storage/` 디스크 용량을 확인한다.
- Worker 로그에서 ffmpeg 오류를 확인한다.

```bash
df -h
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml logs worker --tail=200
```

## 14. 운영자가 자주 쓰는 명령

```bash
cd /opt/lawcompass

# 권장 배포
bash scripts/oci/deploy.sh

# 권장 DB 백업
bash scripts/oci/backup_postgres.sh

# 상태
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml ps

# 전체 로그
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml logs -f --tail=100

# 특정 서비스 재시작
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml restart gateway

# 전체 재기동
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml up -d

# 중지
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml down

# migration
docker compose --env-file .env -f compose.yaml -f compose.prod.yaml --profile migrate run --rm db-migrate
```

## 15. 운영 전 최종 체크리스트

- [ ] OCI A1 Flex 4 OCPU / 24 GB VM 생성.
- [ ] Boot volume 100~150 GB.
- [ ] Security List/NSG: 22는 내 IP, 80/443은 public.
- [ ] UFW: OpenSSH, 80/tcp, 443/tcp 허용.
- [ ] Docker Engine과 Compose V2 설치.
- [ ] `/opt/lawcompass`에 repository clone.
- [ ] `cp env.oci.example .env` 후 기본 secret 교체, `chmod 600 .env`.
- [ ] OCI 운영은 `STORAGE_DRIVER=local`.
- [ ] 비용 방지를 위해 OpenAI frame analysis 기본 OFF.
- [ ] 도메인 운영 시 `.env`의 `LAWCOMPASS_SITE_ADDRESS`와 `CADDY_ACME_EMAIL` 설정.
- [ ] `bash scripts/oci/deploy.sh`.
- [ ] `/health`, `/ready`, 브라우저 접속 확인.
- [ ] DB/스토리지 백업 명령을 한 번 실행해 성공 확인.

## 16. 공식 참고 자료

- Oracle Cloud Always Free Resources: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- Oracle Cloud Free Tier 개요: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm
- Oracle Cloud Free Tier 서비스 목록: https://www.oracle.com/cloud/free/
- OCI Ubuntu 네트워크 포트 안내: https://blogs.oracle.com/developers/enabling-network-traffic-to-ubuntu-images-in-oracle-cloud-infrastructure
- Docker Engine on Ubuntu 공식 설치 문서: https://docs.docker.com/engine/install/ubuntu/
- Caddy Automatic HTTPS 문서: https://caddyserver.com/docs/automatic-https
