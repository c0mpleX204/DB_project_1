from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_v1_router
from app.core import settings
from app.core.db import close_connection_pool, init_connection_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_connection_pool()
    try:
        yield
    finally:
        close_connection_pool()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    @app.get("/")
    def root():
        return {"message": "DB Project 1 API is running", "docs": "/docs"}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


app = create_app()