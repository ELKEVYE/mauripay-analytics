from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    allowed_origins = [
        origin.strip()
        for origin in os.environ.get(
            "MAURIPAY_CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        ).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(ingest_router)
    app.include_router(detect_router)
    app.include_router(stats_router)
    app.include_router(timeseries_router)
    app.include_router(geo_router)
    return app


app = create_app()
