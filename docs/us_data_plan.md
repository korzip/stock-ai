# 미국(US) 데이터 계획 (무료 + 가벼운 구성)

## 목표
- 일봉(1d) 중심으로 시작
- 실시간/분봉은 추후 확장

## 무료 소스 후보 (장단점)
- Stooq: 무료 EOD, 안정적이지만 공식 SLA 없음
- Alpha Vantage: 무료, 분봉 가능(5분), 요청 제한 강함
- Yahoo Finance: 비공식, 약관/안정성 리스크

## MVP 권장안
- Stooq를 기본 소스로 사용
- 필요 시 Alpha Vantage를 보조로 사용

## 유니버스(1차)
- NASDAQ-100 또는 S&P 500 일부
- 무료 제한 고려해 100~200 종목으로 제한

## 파이프라인 구조
1) `sync_us_instruments.py`로 종목 리스트 적재
2) `ingest_us_daily.py`로 일봉 적재
3) `validate_us_daily.py`로 누락 검증
4) `repair_us_daily.py`로 누락 복구

## 스키마 정렬
- `PriceBar` 사용, `timeframe="1d"`
- `Instrument` market_code="US", currency="USD"

## 다음 단계
1) 소스 확정 (Stooq vs Alpha Vantage)
2) 유니버스 확정 (NASDAQ-100 권장)
3) 스케줄러/검증/복구 자동화
