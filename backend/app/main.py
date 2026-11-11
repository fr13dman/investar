import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, companies, market, watchlists
from app.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    from app.migrate import upgrade_head

    upgrade_head()
    scheduler = None
    if settings.enable_scheduler:
        from app.scheduler import build_scheduler

        scheduler = build_scheduler()
        scheduler.start()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


def create_app(use_lifespan: bool = True) -> FastAPI:
    app = FastAPI(title="Investar API", version="0.1.0", lifespan=lifespan if use_lifespan else None)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for r in (market.router, watchlists.router, admin.router, companies.router):
        app.include_router(r)

    @app.get("/api/health")
    def health():
        return {"ok": True}

    return app


app = create_app()
