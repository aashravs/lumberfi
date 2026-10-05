"""
Commissions endpoints with server-side RBAC and filtering.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query

from backend.app.api.deps import get_rbac_filter, require_authenticated_user
from backend.app.db.connection import get_db

router = APIRouter(tags=["commissions"])


@router.get("/api/commissions")
def list_commissions(
    owner: Optional[str] = Query(None, description="Filter by deal_owner"),
    deal_id: Optional[str] = Query(None, description="Filter by deal_id"),
    in_plan: Optional[bool] = Query(None, description="Filter in_plan deals"),
    sort: str = Query("-close_date", description="Field to sort by, prefix with - for desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
    database=Depends(get_db),
):
    """
    List calculated commissions with role-based scoping:
    - AE: see only own commissions.
    - Manager: see only team commissions.
    - Admin: see all commissions.
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

    if in_plan is not None:
        query["in_plan"] = in_plan

    sort_field = sort.lstrip("-")
    sort_dir = -1 if sort.startswith("-") else 1

    total = database.commissions.count_documents(query)
    cursor = (
        database.commissions.find(query, {"_id": 0})
        .sort(sort_field, sort_dir)
        .skip(offset)
        .limit(limit)
    )
    commissions = list(cursor)

    return {
        "commissions": commissions,
        "total": total,
        "limit": limit,
        "offset": offset,
    }
