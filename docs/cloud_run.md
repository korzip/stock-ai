# Cloud Run 배포 가이드 (스테이징/프로덕션)

## 1) 전제
- GCP 프로젝트: `gen-lang-client-0750138661`
- 리전: `asia-northeast3`
- 서비스: `stock-ai-backend`, `stock-ai-mcp`
- 인증 방식: GitHub Actions + Workload Identity Federation(WIF)

## 2) 필요한 리소스
### Cloud SQL (Postgres)
- 인스턴스 생성 후 접속 문자열 확보
- `CLOUD_SQL_CONNECTION_NAME` 사용

### Secret
- `OPENAI_API_KEY`
- `DATABASE_URL`
- `MCP_SERVER_URL`
- `OPENAI_MODEL`

## 3) GitHub Actions 시크릿
GitHub 저장소 Settings → Secrets and variables → Actions에 등록:
- `GCP_WIF_PROVIDER`
- `GCP_SERVICE_ACCOUNT`
- `GCP_PROJECT_ID`
- `CLOUD_SQL_CONNECTION_NAME`
- `DATABASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `MCP_SERVER_URL`

## 4) 배포 워크플로우
- `/.github/workflows/deploy-backend.yml`
- `/.github/workflows/deploy-mcp.yml`

## 5) 로컬에서 수동 배포
### 백엔드
```bash
cd /Users/hh535/private-project/trade-recommend/stock-ai
export PROJECT_ID=gen-lang-client-0750138661
export REGION=asia-northeast3
export CLOUD_SQL_CONNECTION_NAME=...
export DATABASE_URL=...
export OPENAI_API_KEY=...
export OPENAI_MODEL=gpt-4.1-mini
export MCP_SERVER_URL=...
./scripts/cloudrun_deploy_backend.sh
```

### MCP
```bash
cd /Users/hh535/private-project/trade-recommend/stock-ai
export PROJECT_ID=gen-lang-client-0750138661
export REGION=asia-northeast3
./scripts/cloudrun_deploy_mcp.sh
```

## 6) 스테이징/프로덕션
- 스테이징: 서비스 이름에 `-staging` 접미사 사용 권장
- 프로덕션: `stock-ai-backend`, `stock-ai-mcp`

## 7) 참고
- Cloud Run 환경변수는 Secret Manager 연동 권장
- `MCP_SERVER_URL`은 MCP 서비스의 `/sse` 엔드포인트
