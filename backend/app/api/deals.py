"""
Deals endpoints with server-side RBAC and query filtering.
"""

from datetime import datetime, date, time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query

from backend.app.api.deps import get_rbac_filter, require_authenticated_user
from backend.app.db.connection import get_db, db

router = APIRouter(tags=["deals"])


def _parse_filter_date(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    try:
        d = date.fromisoformat(val.strip())
        return datetime.combine(d, time.min)
    except Exception:
        return None


@router.get("/api/deals/count")
def get_deals_count(database=Depends(get_db)):
    """Return total deals count in database."""
    count = database.deals.count_documents({})
    return {"count": count}


@router.get("/api/deals")
def list_deals(
    start_date: Optional[str] = Query(None, description="Filter close_date >= YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Filter close_date <= YYYY-MM-DD"),
    deal_status: Optional[str] = Query(None, description="Filter deal_status, e.g. 'Closed Won'"),
    deal_type: Optional[str] = Query(None, description="Filter deal_type, e.g. 'New'"),
    owner: Optional[str] = Query(None, description="Filter by deal_owner (if authorized)"),
    sort: str = Query("-close_date", description="Field to sort by, prefix with - for desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
    database=Depends(get_db),
):
    """
    List deals with server-side RBAC scoping and filtering.
    - AE: see only own deals.
    - Manager: see only team deals.
    - Admin: see all deals.
    """
    # 1. Base RBAC filter
    query: Dict[str, Any] = get_rbac_filter(current_user, database)

    # 2. Add optional filters
    if owner and owner.strip():
        owner_clean = owner.strip()
        role = current_user.get("role", "").lower()
        if role == "ae":
            # AE cannot override their own scope to see someone else's deals
            pass
        elif role == "manager":
            # Manager can only filter for an owner on their team (case-insensitive substring match)
            permitted = query.get("deal_owner", {}).get("$in", [])
            matched = [name for name in permitted if owner_clean.lower() in name.lower()]
            query["deal_owner"] = {"$in": matched}
        else:
            # Admin: partial, case-insensitive match on deal_owner
            import re
            query["deal_owner"] = {"$regex": re.escape(owner_clean), "$options": "i"}

    if deal_status:
        query["deal_status"] = deal_status

    if deal_type:
        query["deal_type"] = deal_type

    start_dt = _parse_filter_date(start_date)
    end_dt = _parse_filter_date(end_date)
    if start_dt or end_dt:
        date_query = {}
        if start_dt:
            date_query["$gte"] = start_dt
        if end_dt:
            # End of day
            date_query["$lte"] = datetime.combine(end_dt.date(), time.max)
        query["close_date"] = date_query

    # 3. Sorting
    sort_field = sort.lstrip("-")
    sort_dir = -1 if sort.startswith("-") else 1

    total = database.deals.count_documents(query)
    cursor = (
        database.deals.find(query, {"_id": 0})
        .sort(sort_field, sort_dir)
        .skip(offset)
        .limit(limit)
    )
    deals = list(cursor)

    deal_ids = [d.get("deal_id") for d in deals if d.get("deal_id")]
    if deal_ids:
        comm_map = {
            c["deal_id"]: c
            for c in database.commissions.find(
                {"deal_id": {"$in": deal_ids}},
                {"_id": 0, "deal_id": 1, "arr": 1, "arr_commission": 1, "implementation_commission": 1},
            )
        }
        for d in deals:
            c = comm_map.get(d.get("deal_id"))
            if c:
                d["arr"] = c.get("arr", d.get("tcv_year1", 0.0))
                d["commission"] = round(
                    c.get("arr_commission", 0.0) + c.get("implementation_commission", 0.0), 2
                )
            else:
                d["arr"] = d.get("tcv_year1", 0.0)
                d["commission"] = 0.0

    return {
        "deals": deals,
        "total": total,
        "limit": limit,
        "offset": offset,
    }
