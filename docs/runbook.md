# 동작 매뉴얼 (Runbook)

이 문서는 현재 프로젝트를 로컬에서 실행/운영하기 위한 절차를 정리한 매뉴얼입니다.

## 0) 기본 경로
- 루트: `/Users/hh535/private-project/trade-recommend/stock-ai`

## 1) 인프라 실행 (Postgres/Redis)
```bash
cd /Users/hh535/private-project/trade-recommend/stock-ai
docker compose -f infra/docker-compose.yml up -d
```

## 2) MCP 서버 실행
```bash
cd /Users/hh535/private-project/trade-recommend/stock-ai/mcp
source .venv/bin/activate
uvicorn http_app:app --reload --port 9000
```

## 3) 백엔드 실행
```bash
cd /Users/hh535/private-project/trade-recommend/stock-ai/backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

## 4) Flutter 앱 실행
```bash
cd /Users/hh535/private-project/trade-recommend/stock-ai/mobile
flutter run
```

## 5) AI 모드 전환
```bash
cd /Users/hh535/private-project/trade-recommend/stock-ai
./scripts/set_ai_mode.sh rule   # 규칙 기반
./scripts/set_ai_mode.sh llm    # LLM 기반
```

LLM 모드 시 필수 환경변수(`backend/.env`):
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `MCP_SERVER_URL` (예: ngrok URL + `/sse`)

## 6) KR 데이터 (DART 기반 종목 + 일봉)

### KR 종목 동기화 (DART corpCode)
```bash
cd /Users/hh535/private-project/trade-recommend/stock-ai/backend
source .venv/bin/activate
export DART_API_KEY=...
python -m app.sync_kr_instruments_dart
```

### KR 상위 200개 일봉 적재 (DART 목록 기반 대체)
> pykrx 티커 리스트가 막힐 때 DART 기반 목록으로 대체합니다.
```bash
python -m app.ingest_kr_daily_top --top 200 --markets KOSPI,KOSDAQ --date 20260109 --from 2025-01-01 --to 2025-12-31
```

### DART 공시 적재 (테스트용 필터)
```bash
python -m app.ingest_dart --from 2025-01-01 --to 2025-01-07 --stock-codes 005930 --limit 20
```

## 7) US 데이터 (일봉)

### US 종목 동기화
```bash
python -m app.sync_us_instruments
```

### US 일봉 적재 (AAPL 예시)
```bash
python -m app.ingest_us_daily --symbol AAPL --from 2024-01-01 --to 2024-12-31
```

## 8) 검증/복구

### KR 검증/복구
```bash
python -m app.validate_kr_daily --days 30 --limit 50
python -m app.repair_kr_daily --days 30 --limit 50
```

### US 검증/복구
```bash
python -m app.validate_us_daily --days 30 --symbol AAPL --ref AAPL
python -m app.repair_us_daily --days 30 --limit 50
```

## 9) DART 조회 API
```bash
curl "http://127.0.0.1:8000/events/dart?stock_code=005930&limit=20"
```

## 10) 원클릭 실행
```bash
cd /Users/hh535/private-project/trade-recommend/stock-ai
./scripts/dev_up.sh
```

## 11) 주의사항
- KR 가격 데이터는 pykrx 접근 상태에 따라 일부 종목이 빈 데이터일 수 있음
- DART API 키는 채팅/공개 로그에 절대 노출하지 말 것
