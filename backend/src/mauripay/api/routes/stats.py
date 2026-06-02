from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("/health")
def stats_health() -> dict[str, str]:
    return {"status": "ready", "module": "stats"}
