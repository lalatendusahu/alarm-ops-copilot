"""Launches the Chainlit app without going through the `chainlit` CLI.

The CLI (`chainlit.cli`) calls `nest_asyncio.apply()` at import time, which
monkey-patches asyncio's Task/event-loop classes process-wide to allow reentrant
event loops. That patch corrupts anyio's cancel-scope bookkeeping for any anyio-based
client used later in the process -- including the MCP SDK's streamable-http client --
producing "Attempted to exit a cancel scope that isn't the current task's current
cancel scope" even though the underlying connection succeeds. This was confirmed by
running the same MCP client code standalone (works) versus under `chainlit run`
(breaks), and by tracing the patch to that single `nest_asyncio.apply()` call, which
only chainlit.cli imports.

This launcher reproduces what `chainlit.cli.run_chainlit()` does -- load the target
module, wire up config, mount the ASGI app, serve with uvicorn -- without importing
chainlit.cli at all, so nest_asyncio is never applied.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import uvicorn  # noqa: E402
from chainlit.auth import ensure_jwt_secret  # noqa: E402
from chainlit.config import config, load_module  # noqa: E402
from chainlit.markdown import init_markdown  # noqa: E402

TARGET = str(Path(__file__).resolve().parent / "chainlit_app.py")

HOST = os.environ.get("CHAINLIT_HOST", "0.0.0.0")
PORT = int(os.environ.get("CHAINLIT_PORT", "8000"))

config.run.host = HOST
config.run.port = PORT
config.run.headless = True

from chainlit.server import app  # noqa: E402

config.run.module_name = TARGET
load_module(config.run.module_name)
ensure_jwt_secret()
init_markdown(config.root)

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
