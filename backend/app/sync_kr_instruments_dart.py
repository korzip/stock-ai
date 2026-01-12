import os
import zipfile
from io import BytesIO
from xml.etree import ElementTree

import requests
from sqlmodel import SQLModel, Session, select

from .db import engine
from .models import Instrument


def _fetch_corp_codes(api_key: str) -> bytes:
    resp = requests.get(
        "https://opendart.fss.or.kr/api/corpCode.xml",
        params={"crtfc_key": api_key},
        timeout=30,
    )
    resp.raise_for_status()
    content = resp.content
    # ZIP files start with PK\x03\x04
    if not content.startswith(b"PK\x03\x04"):
        text = resp.text.strip()
        raise RuntimeError(f"DART non-zip response: {text[:500]}")
    return content


def _parse_corp_xml(xml_bytes: bytes):
    root = ElementTree.fromstring(xml_bytes)
    for item in root.findall("list"):
        corp_code = (item.findtext("corp_code") or "").strip()
        stock_code = (item.findtext("stock_code") or "").strip()
        corp_name = (item.findtext("corp_name") or "").strip()
        if not stock_code:
            continue
        yield corp_code, stock_code, corp_name


def main() -> None:
    api_key = os.getenv("DART_API_KEY")
    if not api_key:
        raise RuntimeError("DART_API_KEY is not set.")

    SQLModel.metadata.create_all(engine)

    zipped = _fetch_corp_codes(api_key)
    with zipfile.ZipFile(BytesIO(zipped)) as zf:
        names = zf.namelist()
        if not names:
            raise RuntimeError("DART corpCode zip is empty.")
        xml_bytes = zf.read(names[0])

    total = 0
    with Session(engine) as session:
        for corp_code, stock_code, corp_name in _parse_corp_xml(xml_bytes):
            stmt = select(Instrument).where(
                Instrument.market_code == "KR", Instrument.symbol == stock_code
            )
            inst = session.exec(stmt).first()
            if inst:
                inst.name = corp_name
                inst.currency = "KRW"
            else:
                session.add(
                    Instrument(
                        market_code="KR",
                        symbol=stock_code,
                        name=corp_name,
                        currency="KRW",
                    )
                )
            total += 1
        session.commit()

    print(f"KR instruments synced via DART corpCode: {total}")


if __name__ == "__main__":
    main()
