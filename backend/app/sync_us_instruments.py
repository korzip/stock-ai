import csv
import io
import requests

from sqlmodel import SQLModel, Session, select

from .db import engine
from .models import Instrument


NASDAQ_100_URL = "https://datahub.io/core/nasdaq-listings/r/nasdaq-listed-symbols.csv"


def main() -> None:
    SQLModel.metadata.create_all(engine)
    resp = requests.get(NASDAQ_100_URL, timeout=30)
    resp.raise_for_status()

    rows = []
    reader = csv.DictReader(io.StringIO(resp.text))
    for row in reader:
        symbol = row.get("Symbol")
        name = row.get("Security Name")
        if not symbol or not name:
            continue
        rows.append((symbol.strip(), name.strip()))

    with Session(engine) as session:
        for symbol, name in rows:
            stmt = select(Instrument).where(
                Instrument.market_code == "US", Instrument.symbol == symbol
            )
            inst = session.exec(stmt).first()
            if inst:
                inst.name = name
                inst.currency = "USD"
                inst.exchange = "NASDAQ"
            else:
                session.add(
                    Instrument(
                        market_code="US",
                        symbol=symbol,
                        name=name,
                        currency="USD",
                        exchange="NASDAQ",
                    )
                )
        session.commit()

    print(f"US instruments synced: {len(rows)} tickers")


if __name__ == "__main__":
    main()
