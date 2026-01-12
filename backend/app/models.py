from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel


class Instrument(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    market_code: str  # "KR" or "US"
    symbol: str  # KR: "005930", US: "AAPL"
    name: str
    currency: str  # "KRW" or "USD"
    exchange: Optional[str] = None


class DailyPrice(SQLModel, table=True):
    instrument_id: int = Field(foreign_key="instrument.id", primary_key=True)
    trading_date: date = Field(primary_key=True)
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None


class PriceBar(SQLModel, table=True):
    instrument_id: int = Field(foreign_key="instrument.id", primary_key=True)
    timeframe: str = Field(primary_key=True)  # "1d"
    trading_date: date = Field(primary_key=True)
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None


class CorpEvent(SQLModel, table=True):
    rcept_no: str = Field(primary_key=True)
    corp_code: str
    stock_code: Optional[str] = None
    corp_name: str
    report_nm: str
    published_at: date
    source_url: Optional[str] = None
