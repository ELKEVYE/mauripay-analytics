from __future__ import annotations

from mauripay.api.routes.detect import router as detect_router
from mauripay.api.routes.geo import router as geo_router
from mauripay.api.routes.ingest import router as ingest_router
from mauripay.api.routes.stats import router as stats_router
from mauripay.api.routes.timeseries import router as timeseries_router

__all__ = [
    "detect_router",
    "geo_router",
    "ingest_router",
    "stats_router",
    "timeseries_router",
]
