import argparse
import os
from datetime import date, datetime, timedelta
from typing import List

import pandas as pd
from pykrx import stock
from sqlmodel import Session, select

from .db import engine
from .ingest_kr_daily import main as ingest_single
from .models import Instrument


def _latest_trading_day() -> str:
    override = os.getenv("KRX_TRADING_DAY")
    if override:
        return override
    today = date.today().strftime("%Y%m%d")
    if stock.get_market_ticker_list(today, market="KOSPI"):
        return today
    for offset in range(1, 10):
        day = (date.today() - timedelta(days=offset)).strftime("%Y%m%d")
        if stock.get_market_ticker_list(day, market="KOSPI"):
            return day
    raise RuntimeError("No trading day found in the last 10 days.")


def _default_range(lookback_days: int) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=lookback_days)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _market_cap_for_day(day: str, market: str):
    try:
        df = stock.get_market_cap_by_ticker(day, market=market)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    if "시가총액" not in df.columns:
        return None
    return df


def _find_market_cap_day(
    markets: List[str], lookback: int = 10, base_day: str | None = None
) -> str | None:
    base = date.today() if not base_day else datetime.strptime(base_day, "%Y%m%d").date()
    for offset in range(0, lookback):
        day = (base - timedelta(days=offset)).strftime("%Y%m%d")
        for market in markets:
            df = _market_cap_for_day(day, market)
            if df is not None and not df.empty:
                return day
    return None


def _top_by_market_cap(day: str, markets: List[str], top_n: int) -> List[str]:
    frames = []
    for market in markets:
        df = _market_cap_for_day(day, market)
        if df is None:
            # try a few previous days
            for offset in range(1, 6):
                prev_day = (datetime.strptime(day, "%Y%m%d").date() - timedelta(days=offset)).strftime("%Y%m%d")
                df = _market_cap_for_day(prev_day, market)
                if df is not None:
                    break
        if df is None:
            continue
        df = df.rename(columns={"시가총액": "market_cap"})
        frames.append(df[["market_cap"]])
    if not frames:
        return []
    all_df = pd.concat(frames)
    top = all_df.sort_values("market_cap", ascending=False).head(top_n)
    return list(top.index)


def _top_by_trading_value(day: str, markets: List[str], top_n: int) -> List[str]:
    frames = []
    for market in markets:
        try:
            df = stock.get_market_ohlcv_by_ticker(day, market=market)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        if "거래대금" not in df.columns:
            continue
        df = df.rename(columns={"거래대금": "trading_value"})
        frames.append(df[["trading_value"]])
    if not frames:
        return []
    all_df = pd.concat(frames)
    top = all_df.sort_values("trading_value", ascending=False).head(top_n)
    return list(top.index)


def _top_by_index(day: str, markets: List[str], top_n: int) -> List[str]:
    index_codes = {
        "KOSPI": "1028",  # KOSPI200
        "KOSDAQ": "2037",  # KOSDAQ150
    }
    symbols: List[str] = []
    for market in markets:
        code = index_codes.get(market)
        if not code:
            continue
        try:
            items = stock.get_index_portfolio_deposit_file(code, day)
        except Exception:
            continue
        if isinstance(items, (list, tuple)) and items:
            symbols.extend(list(items))
    # de-dup while preserving order
    seen = set()
    out = []
    for s in symbols:
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out[:top_n]


def _top_by_ticker_list(day: str, markets: List[str], top_n: int) -> List[str]:
    symbols: List[str] = []
    for market in markets:
        try:
            items = stock.get_market_ticker_list(day, market=market)
        except Exception:
            continue
        symbols.extend(items)
    return symbols[:top_n]


def _top_from_db(markets: List[str], top_n: int) -> List[str]:
    with Session(engine) as session:
        rows = session.exec(
            select(Instrument.symbol)
            .where(Instrument.market_code == "KR")
            .where(Instrument.exchange.in_(markets))
        ).all()
        if not rows:
            rows = session.exec(
                select(Instrument.symbol).where(Instrument.market_code == "KR")
            ).all()
    return rows[:top_n]


def _active_tickers(day: str, markets: List[str]) -> set[str]:
    active: set[str] = set()
    for market in markets:
        try:
            items = stock.get_market_ticker_list(day, market=market)
        except Exception:
            items = []
        if items:
            active.update(items)
    return active


def _probe_ohlcv(symbol: str, from_day: str, to_day: str) -> bool:
    try:
        df = stock.get_market_ohlcv_by_date(from_day.replace("-", ""), to_day.replace("-", ""), symbol)
    except Exception:
        return False
    return df is not None and not df.empty


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ingest KR daily bars for top market-cap tickers.")
    parser.add_argument("--top", type=int, default=200, help="Top N by market cap")
    parser.add_argument("--markets", default="KOSPI,KOSDAQ", help="Comma-separated markets")
    parser.add_argument("--date", dest="date_str", help="YYYYMMDD (override trading day)")
    parser.add_argument("--from", dest="from_date", help="YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", help="YYYY-MM-DD")
    args = parser.parse_args(argv)

    lookback_days = int(os.getenv("KR_DAILY_LOOKBACK_DAYS", "30"))
    if args.from_date and args.to_date:
        from_day = args.from_date
        to_day = args.to_date
    else:
        from_day, to_day = _default_range(lookback_days)

    markets = [m.strip().upper() for m in args.markets.split(",") if m.strip()]
    if args.date_str:
        os.environ["KRX_TRADING_DAY"] = args.date_str
    try:
        day = _latest_trading_day()
    except RuntimeError:
        day = None
    symbols = _top_by_market_cap(day, markets, args.top) if day else []
    if not symbols:
        fallback_day = _find_market_cap_day(markets, base_day=day)
        if fallback_day and fallback_day != day:
            day = fallback_day
            symbols = _top_by_market_cap(day, markets, args.top)
    if not symbols and day:
        symbols = _top_by_trading_value(day, markets, args.top)
    if not symbols and day:
        symbols = _top_by_index(day, markets, args.top)
    if not symbols:
        # final fallback: ticker list (not true top, but keeps flow moving)
        fallback_day = day or args.date_str or date.today().strftime("%Y%m%d")
        symbols = _top_by_ticker_list(fallback_day, markets, args.top)
        if symbols:
            print("Warning: Using ticker list fallback (not true top by market cap).")
    if not symbols:
        symbols = _top_from_db(markets, args.top)
        if symbols:
            print("Warning: Using DB instrument fallback (not true top by market cap).")
            print("Note: DART corpCode list used; ordering is not market-cap based.")
    if not symbols:
        raise RuntimeError(
            "No market cap/trading value data found. Try a past --date (e.g. 20240102) or check pykrx access."
        )

    active = _active_tickers(day, markets)
    if active:
        symbols = [s for s in symbols if s in active]
        if len(symbols) < args.top:
            print(
                f"Warning: filtered to {len(symbols)} active tickers on {day} (from {args.top})."
            )
    else:
        print("Warning: active ticker list is empty; cannot filter inactive symbols.")

    if symbols and not _probe_ohlcv(symbols[0], from_day, to_day):
        raise RuntimeError(
            "pykrx OHLCV returned empty. Check date range or pykrx access for price data."
        )

    if len(symbols) < args.top:
        print(
            f"Warning: only {len(symbols)} symbols found (expected {args.top}). "
            "Check KR instruments sync or use a past --date."
        )
    print(f"Top {len(symbols)} KR symbols on {day}: {', '.join(markets)}")
    skipped = 0
    for symbol in symbols:
        try:
            df = stock.get_market_ohlcv_by_date(
                from_day.replace("-", ""), to_day.replace("-", ""), symbol
            )
        except Exception:
            skipped += 1
            continue
        if df is None or df.empty:
            skipped += 1
            continue
        ingest_single(["--symbol", symbol, "--from", from_day, "--to", to_day])
    if skipped:
        print(f"Skipped {skipped} symbols with no OHLCV data.")


if __name__ == "__main__":
    main()
