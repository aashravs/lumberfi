"""
Health-check endpoint for the Lumberfi API.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.app.db.connection import ping_mongodb

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """
    Returns the overall API and database health.

    - 200 with status "ok" when everything is healthy.
    - 503 when the database is unreachable.
    """
    db_ok = ping_mongodb()

    if db_ok:
        return {"status": "ok"}

    return JSONResponse(
        status_code=503,
        content={"status": "error", "detail": "Database unavailable"},
    )
