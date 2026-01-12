import argparse
import io
from datetime import datetime
from typing import List

import pandas as pd
import requests
import yfinance as yf
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import SQLModel, Session, select

from .db import engine
from .models import Instrument, PriceBar


def _parse_day(value: str) -> str:
    return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")


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


def _fetch_yfinance(symbol: str, from_day: str | None, to_day: str | None) -> pd.DataFrame:
    df = yf.download(
        symbol,
        start=from_day,
        end=to_day,
        interval="1d",
        progress=False,
        auto_adjust=False,
        group_by="column",
    )
    return df


def _fetch_stooq(symbol: str, from_day: str | None, to_day: str | None) -> pd.DataFrame:
    stooq_symbol = f"{symbol.lower()}.us"
    url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df.rename(
        columns={
            "Date": "Date",
            "Open": "Open",
            "High": "High",
            "Low": "Low",
            "Close": "Close",
            "Volume": "Volume",
        },
        inplace=True,
    )
    if from_day:
        df = df[df["Date"] >= from_day]
    if to_day:
        df = df[df["Date"] <= to_day]
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)
    return df


def main(argv: list[str] | None = None) -> None:
    SQLModel.metadata.create_all(engine)
    parser = argparse.ArgumentParser(description="Ingest US daily price bars.")
    parser.add_argument("--symbol", required=True, help="US ticker (e.g. AAPL)")
    parser.add_argument("--from", dest="from_date", help="YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", help="YYYY-MM-DD")
    args = parser.parse_args(argv)

    from_day = _parse_day(args.from_date) if args.from_date else None
    to_day = _parse_day(args.to_date) if args.to_date else None

    with Session(engine) as session:
        inst = session.exec(
            select(Instrument).where(
                Instrument.market_code == "US", Instrument.symbol == args.symbol
            )
        ).first()
        if not inst:
            raise RuntimeError(f"Instrument not found for US symbol: {args.symbol}")

        df = _fetch_stooq(args.symbol, from_day, to_day)
        if df.empty:
            df = _fetch_yfinance(args.symbol, from_day, to_day)
        rows = []
        for idx, row in df.iterrows():
            trading_date = idx.date()
            rows.append(
                {
                    "instrument_id": inst.id,
                    "timeframe": "1d",
                    "trading_date": trading_date,
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                }
            )
        _upsert_price_bars(session, rows)
        session.commit()

    print(f"Ingested {len(rows)} US daily bars for {args.symbol}")


if __name__ == "__main__":
    main()
