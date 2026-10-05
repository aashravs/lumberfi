"""
Dashboard endpoints: summary, performance, and trends with server-side RBAC scoping.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends

from backend.app.api.deps import get_rbac_filter, require_authenticated_user
from backend.app.db.connection import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

MONTHLY_TARGET_PER_AE = 100_000.0  # $100,000/month MVP assumption
PLAN_MONTHS = 3  # Q3: July, August, September
TARGET_NOTE = "MVP assumption — target not present in supplied production dataset."


@router.get("/summary")
def get_dashboard_summary(
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
    database=Depends(get_db),
):
    """
    Role-scoped executive summary metrics:
    - AE: metrics for their own deals only.
    - Manager: metrics for their team only.
    - Admin: company-wide metrics.
    """
    scope_filter = get_rbac_filter(current_user, database)

    # 1. Deals aggregation
    deal_pipeline = [
        {"$match": scope_filter},
        {
            "$group": {
                "_id": None,
                "total_revenue": {"$sum": "$tcv_year1"},
                "deal_count": {"$sum": 1},
                "closed_won_count": {
                    "$sum": {"$cond": [{"$eq": ["$deal_status", "Closed Won"]}, 1, 0]}
                },
            }
        },
    ]
    deal_agg = list(database.deals.aggregate(deal_pipeline))
    deal_stats = deal_agg[0] if deal_agg else {
        "total_revenue": 0.0,
        "deal_count": 0,
        "closed_won_count": 0,
    }

    total_revenue = float(deal_stats["total_revenue"] or 0.0)
    deal_count = int(deal_stats["deal_count"] or 0)
    closed_won_deals = int(deal_stats["closed_won_count"] or 0)
    avg_deal_value = round(total_revenue / deal_count, 2) if deal_count > 0 else 0.0

    # 2. Commissions aggregation
    comm_pipeline = [
        {"$match": scope_filter},
        {
            "$group": {
                "_id": None,
                "total_arr": {"$sum": "$arr"},
                "total_arr_comm": {"$sum": "$arr_commission"},
                "total_impl_comm": {"$sum": "$implementation_commission"},
            }
        },
    ]
    comm_agg = list(database.commissions.aggregate(comm_pipeline))
    comm_stats = comm_agg[0] if comm_agg else {
        "total_arr": 0.0,
        "total_arr_comm": 0.0,
        "total_impl_comm": 0.0,
    }
    total_arr = float(comm_stats["total_arr"] or 0.0)
    total_commission = round(
        float(comm_stats["total_arr_comm"] or 0.0) + float(comm_stats["total_impl_comm"] or 0.0),
        2,
    )

    # 3. Payouts aggregation
    payout_pipeline = [
        {"$match": scope_filter},
        {"$group": {"_id": None, "total_payout": {"$sum": "$amount"}}},
    ]
    payout_agg = list(database.payouts.aggregate(payout_pipeline))
    total_payouts = round(float(payout_agg[0]["total_payout"]) if payout_agg else 0.0, 2)

    # 4. Revenue contribution by AE
    ae_pipeline = [
        {"$match": scope_filter},
        {
            "$group": {
                "_id": "$deal_owner",
                "revenue": {"$sum": "$tcv_year1"},
                "deals": {"$sum": 1},
            }
        },
        {"$sort": {"revenue": -1}},
    ]
    ae_list = list(database.deals.aggregate(ae_pipeline))
    revenue_by_ae = [
        {
            "owner": item["_id"] or "Unknown",
            "revenue": round(float(item["revenue"]), 2),
            "deals": item["deals"],
        }
        for item in ae_list
        if item["_id"] is not None
    ]

    top_ae = revenue_by_ae[0] if revenue_by_ae else None
    lowest_ae = revenue_by_ae[-1] if len(revenue_by_ae) > 1 else None

    # 5. Target attainment (MVP assumption)
    role = current_user.get("role", "").lower()
    ae_count = 1 if role == "ae" else max(len(revenue_by_ae), 1)
    target_amount = round(ae_count * MONTHLY_TARGET_PER_AE * PLAN_MONTHS, 2)
    target_attainment_pct = (
        round((total_revenue / target_amount) * 100, 2) if target_amount > 0 else 0.0
    )

    return {
        "role": current_user.get("role"),
        "user_name": current_user.get("name"),
        "total_revenue": total_revenue,
        "total_arr": total_arr,
        "total_commission": total_commission,
        "total_payouts": total_payouts,
        "deal_count": deal_count,
        "closed_won_deals": closed_won_deals,
        "average_deal_value": avg_deal_value,
        "top_ae": top_ae,
        "lowest_ae": lowest_ae,
        "revenue_by_ae": revenue_by_ae,
        "target": {
            "target_amount": target_amount,
            "attainment_pct": target_attainment_pct,
            "target_note": TARGET_NOTE,
        },
    }


@router.get("/performance")
def get_dashboard_performance(
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
    database=Depends(get_db),
):
    """
    Return aggregated performance table by AE, sorted by revenue descending.
    Scoped by role: AE sees only themselves; Manager sees their team; Admin sees all.
    """
    scope_filter = get_rbac_filter(current_user, database)

    # 1. Aggregate deals by owner
    deal_pipeline = [
        {"$match": scope_filter},
        {
            "$group": {
                "_id": "$deal_owner",
                "revenue": {"$sum": "$tcv_year1"},
                "deals": {"$sum": 1},
            }
        },
    ]
    owner_deals = {
        item["_id"]: item for item in database.deals.aggregate(deal_pipeline) if item["_id"]
    }

    # 2. Aggregate commissions by owner
    comm_pipeline = [
        {"$match": scope_filter},
        {
            "$group": {
                "_id": "$deal_owner",
                "arr": {"$sum": "$arr"},
                "commission": {
                    "$sum": {"$add": ["$arr_commission", "$implementation_commission"]}
                },
            }
        },
    ]
    owner_comm = {
        item["_id"]: item for item in database.commissions.aggregate(comm_pipeline) if item["_id"]
    }

    # 3. Aggregate payouts by owner
    payout_pipeline = [
        {"$match": scope_filter},
        {"$group": {"_id": "$deal_owner", "payout": {"$sum": "$amount"}}},
    ]
    owner_payout = {
        item["_id"]: item for item in database.payouts.aggregate(payout_pipeline) if item["_id"]
    }

    # Combine into performance records
    all_owners = sorted(
        set(owner_deals.keys()) | set(owner_comm.keys()) | set(owner_payout.keys())
    )
    performance = []
    target_per_ae = round(MONTHLY_TARGET_PER_AE * PLAN_MONTHS, 2)

    for owner in all_owners:
        d = owner_deals.get(owner, {})
        c = owner_comm.get(owner, {})
        p = owner_payout.get(owner, {})

        rev = round(float(d.get("revenue", 0.0)), 2)
        attainment = round((rev / target_per_ae) * 100, 2) if target_per_ae > 0 else 0.0

        performance.append(
            {
                "owner": owner,
                "revenue": rev,
                "arr": round(float(c.get("arr", 0.0)), 2),
                "deals": int(d.get("deals", 0)),
                "commission": round(float(c.get("commission", 0.0)), 2),
                "payout": round(float(p.get("payout", 0.0)), 2),
                "target": target_per_ae,
                "target_attainment": attainment,
                "target_note": TARGET_NOTE,
            }
        )

    # Sort by revenue descending by default
    performance.sort(key=lambda x: x["revenue"], reverse=True)
    return performance


@router.get("/trends")
def get_dashboard_trends(
    current_user: Dict[str, Any] = Depends(require_authenticated_user),
    database=Depends(get_db),
):
    """
    Return monthly aggregated trends:
    month (YYYY-MM), revenue, ARR, commission, payouts, deals count.
    Scoped by role.
    """
    scope_filter = get_rbac_filter(current_user, database)

    # Deals & Revenue by month (from close_date)
    deal_pipeline = [
        {"$match": scope_filter},
        {
            "$project": {
                "month": {
                    "$dateToString": {
                        "format": "%Y-%m",
                        "date": "$close_date",
                    }
                },
                "tcv_year1": 1,
            }
        },
        {
            "$group": {
                "_id": "$month",
                "revenue": {"$sum": "$tcv_year1"},
                "deals": {"$sum": 1},
            }
        },
    ]
    deal_trends = {
        item["_id"]: item
        for item in database.deals.aggregate(deal_pipeline)
        if item["_id"]
    }

    # Commissions & ARR by month (from close_date)
    comm_pipeline = [
        {"$match": scope_filter},
        {
            "$project": {
                "month": {
                    "$dateToString": {
                        "format": "%Y-%m",
                        "date": "$close_date",
                    }
                },
                "arr": 1,
                "arr_commission": 1,
                "implementation_commission": 1,
            }
        },
        {
            "$group": {
                "_id": "$month",
                "arr": {"$sum": "$arr"},
                "commission": {
                    "$sum": {"$add": ["$arr_commission", "$implementation_commission"]}
                },
            }
        },
    ]
    comm_trends = {
        item["_id"]: item
        for item in database.commissions.aggregate(comm_pipeline)
        if item["_id"]
    }

    # Payouts by month (from payout_date)
    payout_pipeline = [
        {"$match": scope_filter},
        {
            "$project": {
                "month": {
                    "$dateToString": {
                        "format": "%Y-%m",
                        "date": "$payout_date",
                    }
                },
                "amount": 1,
            }
        },
        {"$group": {"_id": "$month", "payouts": {"$sum": "$amount"}}},
    ]
    payout_trends = {
        item["_id"]: item
        for item in database.payouts.aggregate(payout_pipeline)
        if item["_id"]
    }

    all_months = sorted(
        set(deal_trends.keys()) | set(comm_trends.keys()) | set(payout_trends.keys())
    )
    trends = []
    for m in all_months:
        d = deal_trends.get(m, {})
        c = comm_trends.get(m, {})
        p = payout_trends.get(m, {})
        trends.append(
            {
                "month": m,
                "revenue": round(float(d.get("revenue", 0.0)), 2),
                "arr": round(float(c.get("arr", 0.0)), 2),
                "commission": round(float(c.get("commission", 0.0)), 2),
                "payouts": round(float(p.get("payouts", 0.0)), 2),
                "deals": int(d.get("deals", 0)),
            }
        )

    return trends
