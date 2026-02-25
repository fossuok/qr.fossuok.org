"""
Non-invasive performance profiling middleware.

Logs timing for:
  1. Every HTTP request/response cycle (endpoint-level)
  2. Every Supabase DB call (query-level) via a thin wrapper
  3. Supabase auth calls (sign_in_with_oauth, exchange_code_for_session)

All data is written to  logs/perf.log  in the project root.
Nothing in the existing application logic is modified.
"""

import logging
import os
import time
from pathlib import Path
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

LOG_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "perf.log"

perf_logger = logging.getLogger("perf")
perf_logger.setLevel(logging.DEBUG)
perf_logger.propagate = False

_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(message)s", datefmt="%H:%M:%S")
)
perf_logger.addHandler(_handler)


# Request / Response middleware
class PerfMiddleware(BaseHTTPMiddleware):
    """Logs method, path, status code, and wall-clock ms for every request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        perf_logger.info(
            "REQUEST  | %6.0fms | %s %s -> %s",
            elapsed_ms,
            request.method,
            request.url.path,
            response.status_code,
        )
        return response


# Supabase DB-call profiling

def patch_supabase_admin(admin_holder) -> None:
    """
    Monkey-patches the postgrest AsyncQueryRequestBuilder.execute()
    so every DB call is timed and logged.

    Call this once after `supabase_admin.init()` in the lifespan.
    """
    from postgrest._async.request_builder import AsyncQueryRequestBuilder

    if getattr(AsyncQueryRequestBuilder, "_perf_patched", False):
        return  # already patched (e.g. after hot-reload)

    _orig_execute = AsyncQueryRequestBuilder.execute

    async def _timed_execute(self, *args, **kwargs):
        start = time.perf_counter()
        result = await _orig_execute(self, *args, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        row_count = len(result.data) if hasattr(result, "data") and result.data else 0
        perf_logger.info(
            "DB_CALL  | %6.0fms | rows=%d",
            elapsed_ms,
            row_count,
        )
        return result

    AsyncQueryRequestBuilder.execute = _timed_execute
    AsyncQueryRequestBuilder._perf_patched = True


# Sync auth call profiling

def patch_sync_auth(sync_client) -> None:
    """
    Monkey-patches the sync Supabase auth client so that
    sign_in_with_oauth and exchange_code_for_session are timed.
    """
    if getattr(sync_client.auth, "_perf_patched", False):
        return  # already patched (hot-reload guard)

    _orig_exchange = sync_client.auth.exchange_code_for_session

    def _timed_exchange(*args, **kwargs):
        start = time.perf_counter()
        result = _orig_exchange(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        perf_logger.info(
            "AUTH     | %6.0fms | exchange_code_for_session",
            elapsed_ms,
        )
        return result

    sync_client.auth.exchange_code_for_session = _timed_exchange

    _orig_oauth = sync_client.auth.sign_in_with_oauth

    def _timed_oauth(*args, **kwargs):
        start = time.perf_counter()
        result = _orig_oauth(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        perf_logger.info(
            "AUTH     | %6.0fms | sign_in_with_oauth",
            elapsed_ms,
        )
        return result

    sync_client.auth.sign_in_with_oauth = _timed_oauth
    sync_client.auth._perf_patched = True
