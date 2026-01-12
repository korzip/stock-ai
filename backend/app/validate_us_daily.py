import argparse
import io
from datetime import date, datetime, timedelta
from typing import Dict, List

import pandas as pd
import requests
from sqlmodel import Session, SQLModel, select

from .db import engine
from .models import Instrument, PriceBar


def _fetch_stooq_dates(symbol: str, days: int) -> List[date]:
    end = date.today()
    start = end - timedelta(days=days)
    from_day = start.strftime("%Y-%m-%d")
    to_day = end.strftime("%Y-%m-%d")

    stooq_symbol = f"{symbol.lower()}.us"
    url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df = df[(df["Date"] >= from_day) & (df["Date"] <= to_day)]
    df["Date"] = pd.to_datetime(df["Date"])
    return [d.date() for d in df["Date"].tolist()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate US daily bars completeness.")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--ref", default="AAPL", help="Reference symbol for trading days")
    parser.add_argument("--symbol", help="Validate a single US symbol")
    args = parser.parse_args()

    SQLModel.metadata.create_all(engine)
    dates = _fetch_stooq_dates(args.ref, args.days)

    with Session(engine) as session:
        if args.symbol:
            instruments = session.exec(
                select(Instrument).where(
                    Instrument.market_code == "US", Instrument.symbol == args.symbol
                )
            ).all()
        else:
            instruments = session.exec(
                select(Instrument).where(Instrument.market_code == "US")
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
        print(f"OK: no missing US daily bars in last {args.days} days.")
        return

    print(f"Missing US daily bars (last {args.days} days):")
    for symbol, count in sorted(missing_by_symbol.items(), key=lambda x: -x[1]):
        print(f"- {symbol}: {count}")


if __name__ == "__main__":
    main()
