from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.v1 import users, auth, admin, api
from config.supabase import supabase as sync_supabase
from config.supabase import supabase_admin
from middleware.perf_logger import PerfMiddleware, patch_supabase_admin, patch_sync_auth
from services.event import get_active_event


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application-level resources.

    On startup:
    - A persistent async Supabase admin client is initialized.  Its httpx
      connection pool is reused for every DB query, avoiding the ~1 s
      cold-connect per call that the old sync client had.
    - A shared httpx.AsyncClient is created for outgoing HTTP (e.g. email).
    - The active-event cache is pre-warmed.
    """
    # Start persistent async Supabase DB client
    await supabase_admin.init()
    patch_supabase_admin(supabase_admin)  # instrument DB calls -> logs/perf.log

    # Shared HTTP client for email sends
    async with httpx.AsyncClient(timeout=15.0) as http_client:
        app.state.http_client = http_client

        # Pre-warm the event cache (best-effort)
        try:
            await get_active_event()
        except Exception:
            pass

        yield

    # Gracefully close the async admin client on shutdown
    await supabase_admin.aclose()


patch_sync_auth(sync_supabase)

app: FastAPI = FastAPI(lifespan=lifespan)

# logs every request -> logs/perf.log
app.add_middleware(PerfMiddleware)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(users.router)
app.include_router(api.router)


@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Login page — entry point for everyone."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "message": "Server is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
