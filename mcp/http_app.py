import contextlib

from starlette.applications import Starlette

from tools import mcp


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with mcp.session_manager.run():
        yield


stream_app = mcp.streamable_http_app()
sse_app = mcp.sse_app()

app = Starlette(
    routes=[*stream_app.routes, *sse_app.routes],
    lifespan=lifespan,
)
