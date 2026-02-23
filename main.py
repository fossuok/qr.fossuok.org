from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from routes import users, auth, admin, api


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app: FastAPI = FastAPI(
    lifespan=lifespan
)

templates = Jinja2Templates(directory="templates")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

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
