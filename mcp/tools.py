import os
from datetime import date
from typing import Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from sqlmodel import Session, SQLModel, Field, create_engine, select

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL", ""), echo=False)

mcp = FastMCP("StockAI MCP", stateless_http=True, json_response=True)


class Instrument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    market_code: str
    symbol: str
    name: str
    currency: str


class DailyPrice(SQLModel, table=True):
    instrument_id: int = Field(primary_key=True)
    trading_date: date = Field(primary_key=True)
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: int | None = None


@mcp.tool()
def search_instruments(q: str, market: Optional[str] = None, limit: int = 10):
    """Search instruments by symbol or name. market: KR/US (optional)."""
    market = market.upper() if market else None
    with Session(engine) as session:
        stmt = select(Instrument).where(
            (Instrument.symbol.ilike(f"%{q}%")) | (Instrument.name.ilike(f"%{q}%"))
        )
        if market:
            stmt = stmt.where(Instrument.market_code == market)
        stmt = stmt.limit(max(1, min(limit, 50)))
        items = session.exec(stmt).all()
        return {"items": [i.model_dump() for i in items]}


@mcp.tool()
def get_daily_prices(instrument_id: int, from_date: date, to_date: date):
    """Get daily prices for a given instrument_id within date range."""
    with Session(engine) as session:
        stmt = (
            select(DailyPrice)
            .where(DailyPrice.instrument_id == instrument_id)
            .where(DailyPrice.trading_date >= from_date)
            .where(DailyPrice.trading_date <= to_date)
            .order_by(DailyPrice.trading_date.asc())
        )
        rows = session.exec(stmt).all()
        return {"items": [r.model_dump() for r in rows]}
