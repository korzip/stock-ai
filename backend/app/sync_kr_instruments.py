import argparse
import os
from datetime import date, timedelta

from pykrx import stock
from sqlmodel import SQLModel, Session, select

from .db import engine
from .models import Instrument


def _latest_trading_day() -> str:
    today = date.today().strftime("%Y%m%d")
    tickers_today = stock.get_market_ticker_list(today, market="KOSPI")
    if tickers_today:
        return today
    for offset in range(0, 10):
        day = (date.today() - timedelta(days=offset)).strftime("%Y%m%d")
        tickers = stock.get_market_ticker_list(day, market="KOSPI")
        if tickers:
            return day
    raise RuntimeError("No trading day found in the last 10 days.")


def main() -> None:
    SQLModel.metadata.create_all(engine)
    parser = argparse.ArgumentParser(description="Sync KR instruments.")
    parser.add_argument("--date", dest="date_str", help="YYYYMMDD (override)")
    args = parser.parse_args()

    override = args.date_str or os.getenv("KRX_TRADING_DAY")
    markets = os.getenv("KRX_MARKETS", "KOSPI,KOSDAQ").split(",")
    markets = [m.strip().upper() for m in markets if m.strip()]
    target_day = override or _latest_trading_day()

    total = 0
    counts = {}
    with Session(engine) as session:
        for market in markets:
            tickers = stock.get_market_ticker_list(target_day, market=market)
            if not tickers:
                print(f"Warning: no tickers returned for {market} on {target_day}")
                counts[market] = 0
                continue
            counts[market] = len(tickers)
            for ticker in tickers:
                name = stock.get_market_ticker_name(ticker)
                stmt = select(Instrument).where(
                    Instrument.market_code == "KR", Instrument.symbol == ticker
                )
                inst = session.exec(stmt).first()
                if inst:
                    inst.name = name
                    inst.currency = "KRW"
                    inst.exchange = market
                else:
                    session.add(
                        Instrument(
                            market_code="KR",
                            symbol=ticker,
                            name=name,
                            currency="KRW",
                            exchange=market,
                        )
                    )
            total += len(tickers)
        session.commit()

    if total == 0:
        raise RuntimeError(
            "No KR instruments synced. Try a past --date (e.g. 20240102) or check pykrx access."
        )

    print(f"KR instruments synced for {target_day}: {', '.join(markets)}")
    print(f"Counts: {counts}")


if __name__ == "__main__":
    main()
