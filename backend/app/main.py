"""
Lumberfi Commission Platform – FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.api.health import router as health_router
from backend.app.api.auth import router as auth_router
from backend.app.api.admin import router as admin_router
from backend.app.api.deals import router as deals_router
from backend.app.api.commissions import router as commissions_router
from backend.app.api.payouts import router as payouts_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.calculations import router as calculations_router
from backend.app.db.connection import ping_mongodb, db
from backend.app.db.indexes import ensure_indexes
from backend.app.services.user_service import seed_users

logger = logging.getLogger("lumberfi")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""

    # ── Startup ──────────────────────────────────────────────
    if ping_mongodb():
        logger.info("✅ MongoDB connection verified on startup.")
        # Ensure indexes (unique keys make import/calculation idempotent)
        ensure_indexes(db)
        # Seed demo users from reference workbook
        seed_users(db)
    else:
        logger.error("❌ MongoDB is unreachable – check MONGODB_URI in .env")
        raise RuntimeError(
            "Could not connect to MongoDB on startup. "
            "Verify MONGODB_URI in the .env file."
        )

    yield  # application is running

    # ── Shutdown ─────────────────────────────────────────────
    logger.info("Shutting down Lumberfi API.")


from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings

app = FastAPI(
    title="Lumberfi Commission Platform API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(calculations_router)
app.include_router(deals_router)
app.include_router(commissions_router)
app.include_router(payouts_router)
app.include_router(dashboard_router)


# ── Root endpoint ────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "Lumberfi Commission Platform API"}
