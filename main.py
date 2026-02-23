from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from config import engine, Base
from routes import users, auth, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app: FastAPI = FastAPI(lifespan=lifespan)

templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router)     # /auth/*
app.include_router(admin.router)    # /admin/*
app.include_router(users.router)    # /user/*


# ── Root ───────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Login page — entry point for everyone."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "message": "Server is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=8000)
