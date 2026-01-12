# 진행 기록 (Stock-AI)

이 문서는 지금까지의 구현/설정 진행 내용을 요약한 기록입니다. 이후 작업도 여기 업데이트합니다.

## 1) 기본 환경/레포 구성
- 모노레포: `trade-recommend/stock-ai`
- 구성: `infra/`, `backend/`, `mcp/`, `mobile/`, `scripts/`, `docs/`
- Docker: Postgres + Redis (`infra/docker-compose.yml`)

## 2) 백엔드/DB 기초
- FastAPI + SQLModel
- 기본 API:
  - `/health`
  - `/instruments/search`
  - `/prices/daily` (현재 `PriceBar` 우선 조회)
- DB 모델:
  - `Instrument` (market_code, symbol, name, currency, exchange)
  - `PriceBar` (timeframe=1d)
  - `DailyPrice` (레거시/seed)
  - `CorpEvent` (DART 공시)

## 3) MCP
- MCP 서버: `mcp/http_app.py`
  - `/mcp` (streamable HTTP)
  - `/sse` (OpenAI remote MCP용)
- MCP client: `backend/app/mcp_client.py`
  - SSE/streamable 전환 지원 (`MCP_TRANSPORT=sse`)

## 4) AI (LLM + MCP)
- OpenAI Responses API 연동 (`openai==2.14.0`)
- JSON Schema 구조화 응답
- 규칙 기반 모드 + LLM 모드 토글
  - `AI_MODE=rule` → 규칙 기반
  - `AI_MODE=` → LLM
  - `FORCE_MCP=1` → MCP 결과 강제 사용
- 오류 복구:
  - `previous_response_id` 유실 시 자동 재시도
- 응답 스키마 확장:
  - `resolved_instrument`, `candidates`, `price_summary`, `explanations`, `risk_notes` 등
- 가드레일:
  - 매수/매도 표현 감지 시 위험 문구 강화

## 5) Flutter 앱
- 탭 구조 + 검색/상세/AI 채팅 탭 구현
- KR 공시 카드 표시(상세 화면)
- AI 카드 UI에서 후보/확정 종목 표시
- macOS 네트워크 권한 추가:
  - `mobile/macos/Runner/DebugProfile.entitlements`
  - `mobile/macos/Runner/Release.entitlements`

## 6) 실행/유틸 스크립트
- `scripts/dev_up.sh` : 인프라 + MCP + 백엔드 한번에 실행
- `scripts/tunnel_mcp.sh` : ngrok/cloudflared 터널
- `scripts/set_ai_mode.sh` : rule/llm 모드 전환

## 7) KR 데이터 파이프라인
### KR 종목 동기화
- `python -m app.sync_kr_instruments`
- 거래일 자동 감지 실패 시 `--date YYYYMMDD` 가능
- DART corpCode 대안: `python -m app.sync_kr_instruments_dart`

### KR 일봉
- 단일 종목: `python -m app.ingest_kr_daily --symbol 005930`
- 전체(최근 N일): `python -m app.ingest_kr_daily_bulk`
- 검증: `python -m app.validate_kr_daily --days 30 --limit 50`
- 복구: `python -m app.repair_kr_daily --days 30 --limit 50`

### KR 상위 시총 Top200
- `python -m app.ingest_kr_daily_top --top 200 --markets KOSPI,KOSDAQ --date YYYYMMDD`
- 최근 거래일 시총 컬럼이 비는 경우가 있어 날짜 지정 필요

## 8) DART 공시
- `python -m app.ingest_dart --from YYYY-MM-DD --to YYYY-MM-DD --stock-codes 005930 --limit 20`
- 다건 적재 시 batch upsert(500개)
- 조회 API:
  - `/events/dart?stock_code=005930&limit=20`
  - `/events/dart/summary?stock_code=005930&limit=5`

## 9) US 데이터 (무료/가벼운 구성)
- 소스: Stooq 기본, yfinance 폴백
- 종목 동기화: `python -m app.sync_us_instruments`
- 일봉 적재: `python -m app.ingest_us_daily --symbol AAPL --from 2024-01-01 --to 2024-12-31`
- 검증/복구:
  - `python -m app.validate_us_daily --days 30 --symbol AAPL --ref AAPL`
  - `python -m app.repair_us_daily --days 30 --limit 50`

## 10) 현재 상태
- KR: 일봉 적재/검증 OK (테스트용)
- DART: 특정 종목 필터 적재 OK
- US: AAPL 일봉 적재/검증 OK
- LLM: `gpt-4.1-mini` 정상 동작

## 11) 남은 이슈/다음 작업
- KR 상위 시총 Top200 적재: 시총 데이터가 비는 날짜 케이스 처리 필요
- KR 상위 시총 Top200: 최근 날짜/지정 날짜 기준으로 시총 데이터 있는 날짜로 fallback
- KR 상위 시총 Top200: 거래대금/지수(KOSPI200/KOSDAQ150)/티커리스트 fallback 추가
- KR 상위 시총 Top200: 활성 티커 필터 + OHLCV 사전 점검 추가
- pykrx 티커 리스트 불가 → DART corpCode DB 목록으로 Top N 대체
- US 일괄 적재는 필요 시 `ingest_us_daily_bulk` 사용
- DART 공시 링크 탭(모바일에서 외부 브라우저 열기) 추가 가능
- 6단계 품질 고도화: 후보 선택 UX, 응답 카드 분리 등
