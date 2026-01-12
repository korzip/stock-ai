import argparse
from datetime import date, datetime, timedelta
from typing import List

from pykrx import stock
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import SQLModel, Session, select

from .db import engine
from .models import Instrument, PriceBar


def _parse_day(value: str) -> str:
    return datetime.strptime(value, "%Y-%m-%d").strftime("%Y%m%d")


def _default_range() -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=30)
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
    SQLModel.metadata.create_all(engine)
    parser = argparse.ArgumentParser(description="Ingest KR daily price bars.")
    parser.add_argument("--symbol", required=True, help="KR ticker (e.g. 005930)")
    parser.add_argument("--from", dest="from_date", help="YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", help="YYYY-MM-DD")
    args = parser.parse_args(argv)

    if args.from_date and args.to_date:
        from_day = _parse_day(args.from_date)
        to_day = _parse_day(args.to_date)
    else:
        from_day, to_day = _default_range()

    with Session(engine) as session:
        inst = session.exec(
            select(Instrument).where(
                Instrument.market_code == "KR", Instrument.symbol == args.symbol
            )
        ).first()
        if not inst:
            raise RuntimeError(f"Instrument not found for KR symbol: {args.symbol}")

        df = stock.get_market_ohlcv_by_date(from_day, to_day, args.symbol)
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
        session.commit()

    print(f"Ingested {len(rows)} daily bars for {args.symbol} ({from_day}~{to_day})")


if __name__ == "__main__":
    main()
