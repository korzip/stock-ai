import argparse
import os
from datetime import date, datetime, timedelta
from typing import Dict, List

from pykrx import stock
from sqlmodel import Session, SQLModel, select

from .db import engine
from .models import Instrument, PriceBar


def _trading_days(days: int, ref_symbol: str) -> List[date]:
    end = date.today()
    start = end - timedelta(days=days)
    start_str = start.strftime("%Y%m%d")
    end_str = end.strftime("%Y%m%d")
    df = stock.get_market_ohlcv_by_date(start_str, end_str, ref_symbol)
    return [d.date() for d in df.index]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate KR daily bars completeness.")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    SQLModel.metadata.create_all(engine)
    days = args.days
    ref_symbol = os.getenv("VALIDATE_KR_REF_SYMBOL", "005930")
    dates = _trading_days(days, ref_symbol)

    with Session(engine) as session:
        instruments = session.exec(
            select(Instrument).where(Instrument.market_code == "KR")
        ).all()
        if args.limit:
            instruments = instruments[: args.limit]

        missing_by_symbol: Dict[str, int] = {}
        for inst in instruments:
            rows = session.exec(
                select(PriceBar.trading_date)
                .where(PriceBar.instrument_id == inst.id)
                .where(PriceBar.timeframe == "1d")
                .where(PriceBar.trading_date >= dates[0])
                .where(PriceBar.trading_date <= dates[-1])
            ).all()
            present = set(rows)
            missing = [d for d in dates if d not in present]
            if missing:
                missing_by_symbol[inst.symbol] = len(missing)

    if not missing_by_symbol:
        print(f"OK: no missing daily bars in last {days} days.")
        return

    print(f"Missing daily bars (last {days} days):")
    for symbol, count in sorted(missing_by_symbol.items(), key=lambda x: -x[1]):
        print(f"- {symbol}: {count}")


if __name__ == "__main__":
    main()
