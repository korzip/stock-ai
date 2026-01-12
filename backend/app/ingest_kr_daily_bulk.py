import argparse
import os
from datetime import date, datetime, timedelta
from typing import List

from pykrx import stock
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import SQLModel, Session, select

from .db import engine
from .models import Instrument, PriceBar


def _parse_day(value: str) -> str:
    return datetime.strptime(value, "%Y-%m-%d").strftime("%Y%m%d")


def _default_range(lookback_days: int) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=lookback_days)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def _upsert_price_bars(session: Session, rows: List[dict]) -> None:
    if not rows:
        return
    stmt = insert(PriceBar).values(rows)
    update_cols = {
        "open": stmt.excluded.open,
        "high": stmt.excluded.high,
        "low": stmt.excluded.low,
        "close": stmt.excluded.close,
        "volume": stmt.excluded.volume,
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["instrument_id", "timeframe", "trading_date"],
        set_=update_cols,
    )
    session.exec(stmt)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ingest KR daily bars for all KR instruments.")
    parser.add_argument("--from", dest="from_date", help="YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", help="YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=0, help="Limit symbols for testing")
    args = parser.parse_args(argv)

    lookback_days = int(os.getenv("KR_DAILY_LOOKBACK_DAYS", "2"))
    if args.from_date and args.to_date:
        from_day = _parse_day(args.from_date)
        to_day = _parse_day(args.to_date)
    else:
        from_day, to_day = _default_range(lookback_days)

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        instruments = session.exec(
            select(Instrument).where(Instrument.market_code == "KR")
        ).all()
        if args.limit:
            instruments = instruments[: args.limit]

        total = 0
        for inst in instruments:
            df = stock.get_market_ohlcv_by_date(from_day, to_day, inst.symbol)
            rows = []
            for idx, row in df.iterrows():
                trading_date = idx.date()
                rows.append(
                    {
                        "instrument_id": inst.id,
                        "timeframe": "1d",
                        "trading_date": trading_date,
                        "open": float(row["시가"]),
                        "high": float(row["고가"]),
                        "low": float(row["저가"]),
                        "close": float(row["종가"]),
                        "volume": int(row["거래량"]),
                    }
                )
            _upsert_price_bars(session, rows)
            total += len(rows)
        session.commit()

    print(f"Ingested {total} daily bars for KR ({from_day}~{to_day})")


if __name__ == "__main__":
    main()
