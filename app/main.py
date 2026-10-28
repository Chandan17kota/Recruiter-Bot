"""App factory. Run with:  uvicorn app.main:app --reload   (docs at /docs)"""
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import errors
from app.api.routes_matches import router
from app.config import Settings, load_settings
from app.db.pool import make_pool
from app.services.matching_service import MatchingService


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or load_settings()   # fails fast on bad weights / missing URL

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        pool = make_pool(settings.database_url, settings.statement_timeout_ms, settings.pool_timeout_s)
        # wait=False: the API still starts if the DB is down, and requests return 503.
        pool.open(wait=False)
        app.state.matching_service = MatchingService(pool, settings.weights)
        try:
            yield
        finally:
            pool.close()

    app = FastAPI(
        title="Recruiter Bot",
        version="1.0.0",
        description="Explainable, bidirectional candidate–job matching over hand-written SQL.",
        lifespan=lifespan,
    )
    errors.register(app)
    if settings.cors_origins:
        # Read-only API: only GET is needed cross-origin.
        app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                           allow_methods=["GET"], allow_headers=["*"])
    app.include_router(router)
    return app


logging.basicConfig(level=logging.INFO)


def __getattr__(name):
    # Lazy `app` so importing this module (e.g. in tests) doesn't require DATABASE_URL.
    if name == "app":
        global app
        app = create_app()
        return app
    raise AttributeError(name)
