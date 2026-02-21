from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import engine, Base
from routes import users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create all the tables at the startup
    Base.metadata.create_all(bind=engine)
    yield

    # REMEMBER: when using supabase/postgresql, it needs to close the connection pool


app: FastAPI = FastAPI(lifespan=lifespan)

# add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# add the routes to the app
app.include_router(users.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "version": "0.1.0",
        "message": "Welcome to the FOSSUoK QR-based event registration system!",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "message": "Server is running",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
