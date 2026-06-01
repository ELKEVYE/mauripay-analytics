from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/geo", tags=["geography"])


@router.get("/health")
def geo_health() -> dict[str, str]:
    return {"status": "ready", "module": "geo"}
