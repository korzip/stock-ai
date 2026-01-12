import argparse
from datetime import date, timedelta

from sqlmodel import Session, SQLModel, select

from .db import engine
from .ingest_kr_daily import main as ingest_single
from .models import Instrument, PriceBar


def _date_range(days: int):
    end = date.today()
    start = end - timedelta(days=days)
    cur = start
    out = []
    while cur <= end:
        out.append(cur)
        cur += timedelta(days=1)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair missing KR daily bars.")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    SQLModel.metadata.create_all(engine)
    dates = _date_range(args.days)

    with Session(engine) as session:
        instruments = session.exec(
            select(Instrument).where(Instrument.market_code == "KR")
        ).all()
        if args.limit:
            instruments = instruments[: args.limit]

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
            if not missing:
                continue

            from_date = min(missing).strftime("%Y-%m-%d")
            to_date = max(missing).strftime("%Y-%m-%d")
            print(f"Repairing {inst.symbol} {from_date}~{to_date} ({len(missing)} missing)")

            ingest_single_args = [
                "--symbol",
                inst.symbol,
                "--from",
                from_date,
                "--to",
                to_date,
            ]
            ingest_single(ingest_single_args)  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
