from __future__ import annotations

from fastapi import FastAPI

from mauripay.api.routes import (
    detect_router,
    geo_router,
    ingest_router,
    stats_router,
    timeseries_router,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="MauriPay Analytics API",
        version="0.2.0",
        description="Backend API for MauriPay synthetic data and anomaly detection.",
        openapi_version="3.1.0",
    )
    app.include_router(ingest_router)
    app.include_router(detect_router)
    app.include_router(stats_router)
    app.include_router(timeseries_router)
    app.include_router(geo_router)
    return app


app = create_app()
