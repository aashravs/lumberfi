import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.api.deps import require_admin
from backend.app.db.connection import get_db
from backend.app.services.commission_runner import DEFAULT_PLAN, run_calculations

router = APIRouter(tags=["admin"])


class CalculationRequest(BaseModel):
    """All fields optional: an empty body recalculates every stored deal."""

    deal_ids: Optional[List[str]] = None
    plan_start_date: Optional[datetime.date] = None
    plan_end_date: Optional[datetime.date] = None


@router.post("/api/admin/calculate")
def calculate_commissions(
    request: Optional[CalculationRequest] = None,
    database=Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    if not isinstance(current_user, dict):
        current_user = {"email": "admin@test.com", "role": "Admin"}
    """
    Run / re-run commission and payout calculations for stored deals.

    Idempotent: commissions and payouts are upserted, never duplicated.
    """
    request = request or CalculationRequest()

    if (request.plan_start_date is None) != (request.plan_end_date is None):
        raise HTTPException(
            status_code=422,
            detail="Provide both plan_start_date and plan_end_date, or neither.",
        )

    plan = dict(DEFAULT_PLAN)
    if request.plan_start_date and request.plan_end_date:
        if request.plan_start_date > request.plan_end_date:
            raise HTTPException(
                status_code=422,
                detail="plan_start_date must not be after plan_end_date.",
            )
        plan = {
            "start_date": request.plan_start_date.isoformat(),
            "end_date": request.plan_end_date.isoformat(),
        }

    deal_ids = request.deal_ids
    if deal_ids is not None:
        deal_ids = [str(d).strip() for d in deal_ids if d is not None and str(d).strip()]
        if not deal_ids:
            deal_ids = None

    return run_calculations(database, plan=plan, deal_ids=deal_ids)
