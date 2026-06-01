from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/timeseries", tags=["timeseries"])


@router.get("/health")
def timeseries_health() -> dict[str, str]:
    return {"status": "ready", "module": "timeseries"}
