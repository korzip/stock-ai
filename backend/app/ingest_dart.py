import argparse
import os
from datetime import date, datetime, timedelta
from typing import List

import requests
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import SQLModel, Session

from .db import engine
from .models import CorpEvent


def _default_range() -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=7)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def _upsert_events(session: Session, rows: List[dict], batch_size: int = 500) -> None:
    if not rows:
        return
    for i in range(0, len(rows), batch_size):
        chunk = rows[i : i + batch_size]
        stmt = insert(CorpEvent).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=["rcept_no"],
            set_={
                "corp_code": stmt.excluded.corp_code,
                "stock_code": stmt.excluded.stock_code,
                "corp_name": stmt.excluded.corp_name,
                "report_nm": stmt.excluded.report_nm,
                "published_at": stmt.excluded.published_at,
                "source_url": stmt.excluded.source_url,
            },
        )
        session.exec(stmt)


def main() -> None:
    SQLModel.metadata.create_all(engine)
    parser = argparse.ArgumentParser(description="Ingest DART disclosure list.")
    parser.add_argument("--from", dest="from_date", help="YYYY-MM-DD")
    parser.add_argument("--to", dest="to_date", help="YYYY-MM-DD")
    parser.add_argument("--stock-codes", help="Comma-separated KR stock codes")
    parser.add_argument("--corp-name-contains", help="Filter by corp name substring")
    parser.add_argument("--limit", type=int, default=0, help="Limit rows for testing")
    args = parser.parse_args()

    api_key = os.getenv("DART_API_KEY")
    if not api_key:
        raise RuntimeError("DART_API_KEY is not set.")

    if args.from_date and args.to_date:
        from_day = datetime.strptime(args.from_date, "%Y-%m-%d").strftime("%Y%m%d")
        to_day = datetime.strptime(args.to_date, "%Y-%m-%d").strftime("%Y%m%d")
    else:
        from_day, to_day = _default_range()

    stock_codes = set()
    if args.stock_codes:
        stock_codes = {c.strip() for c in args.stock_codes.split(",") if c.strip()}
    name_filter = args.corp_name_contains

    page = 1
    page_count = 100
    rows: List[dict] = []
    while True:
        resp = requests.get(
            "https://opendart.fss.or.kr/api/list.json",
            params={
                "crtfc_key": api_key,
                "bgn_de": from_day,
                "end_de": to_day,
                "page_no": page,
                "page_count": page_count,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "000":
            raise RuntimeError(f"DART API error: {data.get('message')}")

        items = data.get("list") or []
        if not items:
            break

        for item in items:
            rcept_no = item.get("rcept_no")
            rcept_dt = item.get("rcept_dt")
            if not rcept_no or not rcept_dt:
                continue
            if stock_codes:
                stock_code = item.get("stock_code") or ""
                if stock_code not in stock_codes:
                    continue
            if name_filter:
                corp_name = item.get("corp_name") or ""
                if name_filter not in corp_name:
                    continue
            published_at = datetime.strptime(rcept_dt, "%Y%m%d").date()
            rows.append(
                {
                    "rcept_no": rcept_no,
                    "corp_code": item.get("corp_code", ""),
                    "stock_code": item.get("stock_code") or None,
                    "corp_name": item.get("corp_name", ""),
                    "report_nm": item.get("report_nm", ""),
                    "published_at": published_at,
                    "source_url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
                }
            )
            if args.limit and len(rows) >= args.limit:
                break

        if args.limit and len(rows) >= args.limit:
            break

        total_count = int(data.get("total_count") or 0)
        if page * page_count >= total_count:
            break
        page += 1

    with Session(engine) as session:
        _upsert_events(session, rows)
        session.commit()

    print(f"Ingested {len(rows)} DART disclosures ({from_day}~{to_day})")


if __name__ == "__main__":
    main()
