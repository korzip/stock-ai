import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

load_dotenv()
MCP_URL = os.getenv("MCP_URL", "http://127.0.0.1:9000/mcp")
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "").lower()


@asynccontextmanager
async def mcp_session():
    use_sse = MCP_TRANSPORT == "sse" or MCP_URL.endswith("/sse")
    if use_sse:
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    else:
        async with streamablehttp_client(MCP_URL) as (read, write, _get_session_id):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
