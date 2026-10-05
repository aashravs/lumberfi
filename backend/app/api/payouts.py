"""
Payouts endpoints with server-side RBAC and filtering.
"""

from datetime import datetime, date, time
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query

from backend.app.api.deps import get_rbac_filter, require_authenticated_user
from backend.app.db.connection import get_db

router = APIRouter(tags=["payouts"])


def _parse_filter_date(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        d = date.fromisoformat(val.strip())
        return datetime.combine(d, time.min)
    except Exception:
        return None


@router.get("/api/payouts")
def list_payouts(
    owner: Optional[str] = Query(None, description="Filter by deal_owner"),
    deal_id: Optional[str] = Query(None, description="Filter by deal_id"),
    component: Optional[str] = Query(None, description="Filter by component (Advance, Implementation, Balance, etc.)"),
    start_date: Optional[str] = Query(None, description="Filter payout_date >= YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Filter payout_date <= YYYY-MM-DD"),
    sort: str = Query("-payout_date", description="Field to sort by, prefix with - for desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
    database=Depends(get_db),
):
    """
    List payouts with role-based scoping:
    - AE: see only own payouts.
    - Manager: see only team payouts.
    - Admin: see all payouts.
    """
    query: Dict[str, Any] = get_rbac_filter(current_user, database)

    if owner and owner.strip():
        owner_clean = owner.strip()
        role = current_user.get("role", "").lower()
        if role == "ae":
            pass
        elif role == "manager":
            permitted = query.get("deal_owner", {}).get("$in", [])
            matched = [name for name in permitted if owner_clean.lower() in name.lower()]
            query["deal_owner"] = {"$in": matched}
        else:
            import re
            query["deal_owner"] = {"$regex": re.escape(owner_clean), "$options": "i"}

    if deal_id:
        query["deal_id"] = deal_id

    if component:
        query["component"] = component

    start_dt = _parse_filter_date(start_date)
    end_dt = _parse_filter_date(end_date)
    if start_dt or end_dt:
        date_query = {}
        if start_dt:
            date_query["$gte"] = start_dt
        if end_dt:
            date_query["$lte"] = datetime.combine(end_dt.date(), time.max)
        query["payout_date"] = date_query

    sort_field = sort.lstrip("-")
    sort_dir = -1 if sort.startswith("-") else 1

    total = database.payouts.count_documents(query)
    cursor = (
        database.payouts.find(query, {"_id": 0})
        .sort(sort_field, sort_dir)
        .skip(offset)
        .limit(limit)
    )
    payouts = list(cursor)

    return {
        "payouts": payouts,
        "total": total,
        "limit": limit,
        "offset": offset,
    }
