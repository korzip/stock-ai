import json
import os
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter
from openai import AsyncOpenAI, BadRequestError
from pydantic import BaseModel

from .mcp_client import mcp_session

router = APIRouter(prefix="/ai", tags=["ai"])

SYSTEM_PROMPT = """You are a stock investing assistant for beginners.
- Provide educational guidance, not personalized financial advice.
- Avoid buy/sell instructions.
- Always explain risks and uncertainty.
- When data is needed, use the connected MCP tools.
"""

ASSISTANT_SCHEMA = {
    "type": "object",
    "properties": {
        "resolved_instrument": {
            "type": ["object", "null"],
            "properties": {
                "id": {"type": "integer"},
                "market": {"type": "string"},
                "symbol": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["id", "market", "symbol", "name"],
            "additionalProperties": False,
        },
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "market": {"type": "string"},
                    "symbol": {"type": "string"},
                    "name": {"type": "string"},
                },
                "required": ["id", "market", "symbol", "name"],
                "additionalProperties": False,
            },
        },
        "price_summary": {
            "type": "object",
            "properties": {
                "last_close": {"type": ["number", "null"]},
                "change": {"type": ["number", "null"]},
                "change_pct": {"type": ["number", "null"]},
                "window": {"type": "string"},
            },
            "required": ["last_close", "change", "change_pct", "window"],
            "additionalProperties": False,
        },
        "summary": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}},
        "explanations": {"type": "array", "items": {"type": "string"}},
        "data_used": {"type": "array", "items": {"type": "string"}},
        "risk_notes": {"type": "array", "items": {"type": "string"}},
        "next_actions": {"type": "array", "items": {"type": "string"}},
        "disclaimer": {"type": "string"},
    },
    "required": [
        "resolved_instrument",
        "candidates",
        "price_summary",
        "summary",
        "key_points",
        "explanations",
        "data_used",
        "risk_notes",
        "next_actions",
        "disclaimer",
    ],
    "additionalProperties": False,
}


class ChatIn(BaseModel):
    message: str
    previous_response_id: Optional[str] = None


def _extract_output_text(resp: Any) -> str:
    text = getattr(resp, "output_text", "") or ""
    if text:
        return text
    output = getattr(resp, "output", None) or []
    for item in output:
        for content in getattr(item, "content", []) or []:
            if getattr(content, "type", "") == "output_text":
                return getattr(content, "text", "") or ""
    return ""


def _render_assistant_message(data: Any) -> str:
    if not isinstance(data, dict):
        return str(data)
    lines = []
    candidates = data.get("candidates") or []
    summary = data.get("summary")
    if summary:
        lines.append(str(summary))
    if isinstance(candidates, list) and candidates:
        lines.append("후보 종목:")
        for c in candidates[:5]:
            lines.append(f"- {c.get('symbol')} · {c.get('name')}")
    key_points = data.get("key_points") or []
    if isinstance(key_points, list) and key_points:
        lines.append("핵심 포인트:")
        lines.extend([f"- {p}" for p in key_points])
    explanations = data.get("explanations") or []
    if isinstance(explanations, list) and explanations:
        lines.append("설명:")
        lines.extend([f"- {e}" for e in explanations])
    risk_notes = data.get("risk_notes") or []
    if isinstance(risk_notes, list) and risk_notes:
        lines.append("리스크/주의:")
        lines.extend([f"- {r}" for r in risk_notes])
    disclaimer = data.get("disclaimer")
    if disclaimer:
        lines.append(str(disclaimer))
    return "\n".join(lines).strip() or "응답을 받았지만 표시할 내용이 없습니다."


def _content_to_text(result: Any) -> str:
    content = getattr(result, "content", None) or []
    for item in content:
        text = getattr(item, "text", None)
        if isinstance(text, str) and text:
            return text
    return ""


def _parse_tool_json(result: Any) -> Dict[str, Any]:
    raw = _content_to_text(result)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def _pick_instrument(items: List[Dict[str, Any]], q: str) -> Optional[Dict[str, Any]]:
    if not items:
        return None
    q_norm = q.strip().lower()
    for item in items:
        symbol = str(item.get("symbol", "")).lower()
        if symbol == q_norm:
            return item
    if len(items) == 1:
        return items[0]
    return None


def _summarize_prices(prices: List[Dict[str, Any]]) -> Dict[str, Any]:
    closes = [p for p in prices if p.get("close") is not None]
    if not closes:
        return {"last_close": None, "change": None, "points": 0}
    first = closes[0]["close"]
    last = closes[-1]["close"]
    change = None
    change_pct = None
    if isinstance(first, (int, float)) and isinstance(last, (int, float)):
        change = last - first
        if first:
            change_pct = (change / first) * 100
    return {
        "last_close": last,
        "change": change,
        "change_pct": change_pct,
        "points": len(closes),
    }


def _candidate_list(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "id": i.get("id"),
            "market": i.get("market_code"),
            "symbol": i.get("symbol"),
            "name": i.get("name"),
        }
        for i in items[:5]
    ]


def _resolved_instrument(item: Dict[str, Any] | None) -> Dict[str, Any] | None:
    if not item:
        return None
    return {
        "id": item.get("id"),
        "market": item.get("market_code"),
        "symbol": item.get("symbol"),
        "name": item.get("name"),
    }


def _enforce_guardrails(data: Dict[str, Any]) -> Dict[str, Any]:
    text_blob = " ".join(
        [
            str(data.get("summary", "")),
            " ".join(data.get("key_points", []) or []),
            " ".join(data.get("explanations", []) or []),
            " ".join(data.get("next_actions", []) or []),
        ]
    ).lower()
    forbidden = ["매수", "매도", "buy", "sell", "추천"]
    if any(w in text_blob for w in forbidden):
        data["risk_notes"] = list(set((data.get("risk_notes") or []) + ["개별 매수/매도 지시는 제공하지 않습니다."]))
        data["disclaimer"] = "교육/정보 목적이며 투자 조언이 아닙니다."
    return data


async def _mcp_lookup(msg: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    trace: List[Dict[str, Any]] = []
    async with mcp_session() as session:
        search = await session.call_tool(
            "search_instruments", arguments={"q": msg, "limit": 5}
        )
        search_data = _parse_tool_json(search)
        trace.append(
            {"tool": "search_instruments", "args": {"q": msg, "limit": 5}, "result": search_data}
        )
        items = search_data.get("items") or []
        instrument = _pick_instrument(items, msg)
        if not instrument:
            return None, [], trace

        instrument_id = instrument.get("id")
        prices: List[Dict[str, Any]] = []
        if instrument_id is not None:
            from_date = (date.today() - timedelta(days=30)).isoformat()
            to_date = date.today().isoformat()
            prices_resp = await session.call_tool(
                "get_daily_prices",
                arguments={
                    "instrument_id": instrument_id,
                    "from_date": from_date,
                    "to_date": to_date,
                },
            )
            prices_data = _parse_tool_json(prices_resp)
            trace.append(
                {
                    "tool": "get_daily_prices",
                    "args": {
                        "instrument_id": instrument_id,
                        "from_date": from_date,
                        "to_date": to_date,
                    },
                    "result": prices_data,
                }
            )
            prices = prices_data.get("items") or []

            if not prices:
                prices_resp = await session.call_tool(
                    "get_daily_prices",
                    arguments={
                        "instrument_id": instrument_id,
                        "from_date": "2026-01-01",
                        "to_date": "2026-01-31",
                    },
                )
                prices_data = _parse_tool_json(prices_resp)
                trace.append(
                    {
                        "tool": "get_daily_prices",
                        "args": {
                            "instrument_id": instrument_id,
                            "from_date": "2026-01-01",
                            "to_date": "2026-01-31",
                        },
                        "result": prices_data,
                    }
                )
                prices = prices_data.get("items") or []

    return instrument, prices, trace


async def _rule_based_response(msg: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    instrument, prices, trace = await _mcp_lookup(msg)
    used_tools = [t["tool"] for t in trace]
    if not instrument:
        candidates = []
        if trace and trace[0].get("result", {}).get("items"):
            candidates = _candidate_list(trace[0]["result"]["items"])
        summary_text = f"'{msg}'에 해당하는 종목을 찾지 못했습니다."
        if candidates:
            summary_text = "여러 후보가 있습니다. 종목을 선택해 주세요."
        return (
            {
                "resolved_instrument": None,
                "candidates": candidates,
                "price_summary": {
                    "last_close": None,
                    "change": None,
                    "change_pct": None,
                    "window": "N/A",
                },
                "summary": summary_text,
                "key_points": ["티커/종목코드/이름을 더 정확히 입력해 주세요."],
                "explanations": [],
                "data_used": used_tools,
                "risk_notes": [
                    "데이터 지연/누락 가능성이 있습니다.",
                ],
                "next_actions": ["정확한 티커 또는 종목코드를 다시 입력"],
                "disclaimer": "교육/정보 목적이며 투자 조언이 아닙니다.",
            },
            trace,
        )

    summary = _summarize_prices(prices)
    last_close = summary.get("last_close")
    change = summary.get("change")
    points = summary.get("points", 0)
    name = instrument.get("name")
    symbol = instrument.get("symbol")
    market = instrument.get("market_code")
    currency = instrument.get("currency")

    key_points = [
        f"{symbol} · {name} ({market}, {currency})",
        f"가격 데이터 포인트: {points}개",
    ]
    if last_close is not None:
        key_points.append(f"마지막 종가: {last_close}")
    if change is not None:
        key_points.append(f"기간 변동: {change:+}")

    return (
        {
            "resolved_instrument": _resolved_instrument(instrument),
            "candidates": [],
            "price_summary": {
                "last_close": last_close,
                "change": change,
                "change_pct": summary.get("change_pct"),
                "window": "recent 30d",
            },
            "summary": f"{symbol} {name} 데모 조회 결과입니다.",
            "key_points": key_points,
            "explanations": [
                "현재는 일봉 기반으로 간단 요약만 제공합니다.",
            ],
            "data_used": used_tools,
            "risk_notes": [
                "데이터는 데모 시드 기반일 수 있습니다.",
                "투자에는 원금 손실 위험이 있습니다.",
            ],
            "next_actions": [
                "더 긴 기간 데이터를 붙이려면 데이터 소스를 연동하세요.",
                "관심 종목으로 등록해 추적해 보세요.",
            ],
            "disclaimer": "교육/정보 목적이며 투자 조언이 아닙니다.",
        },
        trace,
    )


@router.post("/chat")
async def chat(inp: ChatIn):
    msg = inp.message.strip()
    if not msg:
        return {"assistant_message": "메시지를 입력해 주세요."}

    api_key = os.getenv("OPENAI_API_KEY")
    ai_mode = os.getenv("AI_MODE", "").lower()
    force_mcp = os.getenv("FORCE_MCP", "").lower() in {"1", "true", "yes"}
    if not api_key or ai_mode == "rule":
        data, trace = await _rule_based_response(msg)
        data = _enforce_guardrails(data)
        return {
            "data": data,
            "assistant_message": _render_assistant_message(data),
            "mcp_trace": trace,
        }

    model = os.getenv("OPENAI_MODEL", "gpt-5")
    mcp_url = os.getenv("MCP_SERVER_URL") or os.getenv("MCP_URL")
    if not mcp_url:
        data, trace = await _rule_based_response(msg)
        data = _enforce_guardrails(data)
        return {
            "data": data,
            "assistant_message": _render_assistant_message(data),
            "mcp_trace": trace,
        }

    client = AsyncOpenAI(api_key=api_key)
    tool_context = None
    trace: List[Dict[str, Any]] = []
    if force_mcp:
        instrument, prices, trace = await _mcp_lookup(msg)
        tool_context = {
            "instrument": instrument,
            "prices": prices[:10],
            "note": "These are trusted MCP tool results. Use them in the response.",
        }

    input_msgs = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": msg},
    ]
    if tool_context:
        input_msgs.insert(
            1, {"role": "system", "content": f"Tool context JSON: {json.dumps(tool_context)}"}
        )

    try:
        resp = await client.responses.create(
            model=model,
            input=input_msgs,
            previous_response_id=inp.previous_response_id,
            tools=[
                {
                    "type": "mcp",
                    "server_label": "market",
                    "server_description": "Market data & analytics tools for stocks.",
                    "server_url": mcp_url,
                    "require_approval": "never",
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "assistant_response",
                    "strict": True,
                    "schema": ASSISTANT_SCHEMA,
                }
            },
            store=False,
        )
    except BadRequestError as exc:
        msg_text = str(exc)
        if "previous_response_id" in msg_text:
            resp = await client.responses.create(
                model=model,
                input=input_msgs,
                tools=[
                    {
                        "type": "mcp",
                        "server_label": "market",
                        "server_description": "Market data & analytics tools for stocks.",
                        "server_url": mcp_url,
                        "require_approval": "never",
                    }
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "assistant_response",
                        "strict": True,
                        "schema": ASSISTANT_SCHEMA,
                    }
                },
                store=False,
            )
        else:
            raise

    payload_text = _extract_output_text(resp)
    data: Dict[str, Any]
    try:
        data = json.loads(payload_text) if payload_text else {}
    except json.JSONDecodeError:
        data = {"raw": payload_text}

    data = _enforce_guardrails(data)
    return {
        "response_id": getattr(resp, "id", None),
        "data": data,
        "assistant_message": _render_assistant_message(data),
        "mcp_trace": trace,
    }
