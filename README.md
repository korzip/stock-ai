# Stock AI 모노레포

로컬 개발 스택: 백엔드 + MCP + 인프라 + 모바일 앱.

## 빠른 시작 (로컬)

1) 인프라
```
docker compose -f infra/docker-compose.yml up -d
```

2) 백엔드
```
cd backend
python3 -m venv .venv
source .venv/bin/activate
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

3) MCP
```
cd ../mcp
python3 -m venv .venv
source .venv/bin/activate
cp .env.example .env
pip install -r requirements.txt
uvicorn http_app:app --reload --port 9000
```

4) 모바일
```
cd ../mobile
flutter run
```

## 원클릭 실행 (로컬)
```
./scripts/dev_up.sh
```

## MCP 터널링 (OpenAI 원격 MCP)
```
./scripts/tunnel_mcp.sh
```

`MCP_SERVER_URL`은 공개 URL에 `/sse`를 붙여 설정합니다.

## AI 모드 전환
```
./scripts/set_ai_mode.sh rule
./scripts/set_ai_mode.sh llm
```

LLM 모드일 때 `backend/.env`에 아래가 필요합니다.
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `MCP_SERVER_URL`

## 5단계: KR 일봉 + DART 공시

1) KR 종목 동기화 (pykrx)
```
cd backend
source .venv/bin/activate
python -m app.sync_kr_instruments
```

대안: DART corpCode 사용
```
export DART_API_KEY=...
python -m app.sync_kr_instruments_dart
```

2) KR 상위 200개 일봉 적재
```
python -m app.ingest_kr_daily_top --top 200 --markets KOSPI,KOSDAQ --date YYYYMMDD --from 2025-01-01 --to 2025-12-31
```

3) DART 공시 적재 (테스트용 필터)
```
python -m app.ingest_dart --from 2025-01-01 --to 2025-01-07 --stock-codes 005930 --limit 20
```

4) 검증/복구
```
python -m app.validate_kr_daily --days 30 --limit 50
python -m app.repair_kr_daily --days 30 --limit 50
```

## DART 조회 API
```
curl "http://127.0.0.1:8000/events/dart?stock_code=005930&limit=20"
```

## US 일봉

1) US 종목 동기화
```
python -m app.sync_us_instruments
```

2) US 일봉 적재 (AAPL 예시)
```
python -m app.ingest_us_daily --symbol AAPL --from 2024-01-01 --to 2024-12-31
```

3) US 검증/복구
```
python -m app.validate_us_daily --days 30 --symbol AAPL --ref AAPL
python -m app.repair_us_daily --days 30 --limit 50
```

## 문서
- `docs/runbook.md`: 실행/운영 매뉴얼
- `docs/us_data_plan.md`: 미국 데이터 계획
- `docs/progress.md`: 진행 기록
