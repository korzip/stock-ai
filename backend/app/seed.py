from datetime import date

from sqlmodel import SQLModel, Session, select

from .db import engine
from .models import DailyPrice, Instrument, PriceBar


def main():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        if not session.exec(select(Instrument)).first():
            aapl = Instrument(
                market_code="US", symbol="AAPL", name="Apple Inc.", currency="USD"
            )
            s005930 = Instrument(
                market_code="KR", symbol="005930", name="삼성전자", currency="KRW"
            )
            session.add(aapl)
            session.add(s005930)
            session.commit()

        instruments = session.exec(select(Instrument)).all()
        by_symbol = {i.symbol: i.id for i in instruments}

        if not session.exec(select(DailyPrice)).first():
            session.add(
                DailyPrice(
                    instrument_id=by_symbol["AAPL"],
                    trading_date=date(2026, 1, 6),
                    close=200.0,
                    volume=1000000,
                )
            )
            session.add(
                DailyPrice(
                    instrument_id=by_symbol["AAPL"],
                    trading_date=date(2026, 1, 7),
                    close=202.0,
                    volume=1200000,
                )
            )
            session.add(
                DailyPrice(
                    instrument_id=by_symbol["005930"],
                    trading_date=date(2026, 1, 6),
                    close=70000,
                    volume=15000000,
                )
            )
            session.add(
                DailyPrice(
                    instrument_id=by_symbol["005930"],
                    trading_date=date(2026, 1, 7),
                    close=71000,
                    volume=16000000,
                )
            )
            session.commit()

        if not session.exec(select(PriceBar)).first():
            session.add(
                PriceBar(
                    instrument_id=by_symbol["AAPL"],
                    timeframe="1d",
                    trading_date=date(2026, 1, 6),
                    close=200.0,
                    volume=1000000,
                )
            )
            session.add(
                PriceBar(
                    instrument_id=by_symbol["AAPL"],
                    timeframe="1d",
                    trading_date=date(2026, 1, 7),
                    close=202.0,
                    volume=1200000,
                )
            )
            session.add(
                PriceBar(
                    instrument_id=by_symbol["005930"],
                    timeframe="1d",
                    trading_date=date(2026, 1, 6),
                    close=70000,
                    volume=15000000,
                )
            )
            session.add(
                PriceBar(
                    instrument_id=by_symbol["005930"],
                    timeframe="1d",
                    trading_date=date(2026, 1, 7),
                    close=71000,
                    volume=16000000,
                )
            )
            session.commit()

    print("Seed complete.")


if __name__ == "__main__":
    main()
