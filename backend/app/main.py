from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, SQLModel, select

from .ai import router as ai_router
from .db import engine, get_session
from .models import CorpEvent, DailyPrice, Instrument, PriceBar

app = FastAPI(title="StockAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)


@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/instruments/search")
def search_instruments(
    q: str = Query(min_length=1),
    market: Optional[str] = Query(default=None, description="KR or US"),
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
):
    stmt = select(Instrument).where(
        (Instrument.symbol.ilike(f"%{q}%")) | (Instrument.name.ilike(f"%{q}%"))
    )
    if market:
        stmt = stmt.where(Instrument.market_code == market.upper())
    stmt = stmt.limit(limit)
    items = session.exec(stmt).all()
    return {"items": items}


@app.get("/prices/daily")
def get_daily_prices(
    instrument_id: int,
    from_date: date,
    to_date: date,
    session: Session = Depends(get_session),
):
    stmt = (
        select(PriceBar)
        .where(PriceBar.instrument_id == instrument_id)
        .where(PriceBar.timeframe == "1d")
        .where(PriceBar.trading_date >= from_date)
        .where(PriceBar.trading_date <= to_date)
        .order_by(PriceBar.trading_date.asc())
    )
    rows = session.exec(stmt).all()
    if rows:
        return {"items": rows}

    fallback = (
        select(DailyPrice)
        .where(DailyPrice.instrument_id == instrument_id)
        .where(DailyPrice.trading_date >= from_date)
        .where(DailyPrice.trading_date <= to_date)
        .order_by(DailyPrice.trading_date.asc())
    )
    rows = session.exec(fallback).all()
    return {"items": rows}


@app.get("/events/dart")
def get_dart_events(
    stock_code: str | None = Query(default=None, description="KR stock code, e.g. 005930"),
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    stmt = select(CorpEvent)
    if stock_code:
        stmt = stmt.where(CorpEvent.stock_code == stock_code)
    if from_date:
        stmt = stmt.where(CorpEvent.published_at >= from_date)
    if to_date:
        stmt = stmt.where(CorpEvent.published_at <= to_date)
    stmt = stmt.order_by(CorpEvent.published_at.desc()).limit(limit)
    rows = session.exec(stmt).all()
    return {"items": rows}


@app.get("/events/dart/summary")
def get_dart_summary(
    stock_code: str = Query(..., description="KR stock code, e.g. 005930"),
    limit: int = Query(default=5, ge=1, le=50),
    session: Session = Depends(get_session),
):
    stmt = (
        select(CorpEvent)
        .where(CorpEvent.stock_code == stock_code)
        .order_by(CorpEvent.published_at.desc())
        .limit(limit)
    )
    rows = session.exec(stmt).all()
    return {
        "stock_code": stock_code,
        "count": len(rows),
        "items": rows,
    }
