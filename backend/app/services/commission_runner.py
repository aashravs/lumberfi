"""
Calculation runner: stored deals -> engine -> `commissions` + `payouts`.

This module contains NO business rules. It adapts MongoDB documents to the
validated engine (calculate_financials / generate_payouts) and persists the
results idempotently:

  * commissions: one document per deal  (unique index on deal_id)
  * payouts:     keyed by (deal_id, component, sequence)
  * every run stamps its documents with a calculation id; payouts of a deal
    that were not produced by the latest run are removed, so changed inputs
    never leave stale payouts behind.
"""

import datetime
import uuid
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pymongo import ReplaceOne

from backend.app.services.calculation_engine import calculate_financials, generate_payouts

# Commission plan window. This mirrors the hardcoded window in the legacy
# calculateFinancials() (1 Jul 2026 - 30 Sep 2026) and is the default for runs.
DEFAULT_PLAN: Dict[str, str] = {
    "start_date": "2026-07-01",
    "end_date": "2026-09-30",
}

_ENGINE_FIELDS = (
    "deal_id",
    "customer_id",
    "customer_name",
    "deal_name",
    "deal_type",
    "deal_owner",
    "lead_source",
    "partner_name",
    "close_date",
    "deal_status",
    "cancellation_date",
    "tcv_year1",
    "implementation_fee",
    "implementation_payment_terms",
    "billing_type",
    "go_live_date",
    "invoice_payment_terms_days",
)
_DATE_FIELDS = ("close_date", "cancellation_date", "go_live_date")


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _date_to_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    return str(value)


def to_engine_deal(stored: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a stored `deals` document to the engine's canonical input."""
    deal = {field: stored.get(field) for field in _ENGINE_FIELDS}
    for field in _DATE_FIELDS:
        deal[field] = _date_to_iso(deal[field])
    return deal


def calculate_deal(
    deal: Dict[str, Any], plan: Optional[Dict[str, str]] = None
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Run the validated engine for one canonical deal."""
    plan = plan or DEFAULT_PLAN
    financials = calculate_financials(deal, plan)
    payouts = generate_payouts(deal, financials)
    return financials, payouts


def _to_bson(value: Any) -> Any:
    """BSON cannot store datetime.date; store date-only values as midnight."""
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time.min)
    return value


def build_commission_doc(
    deal: Dict[str, Any],
    financials: Dict[str, Any],
    plan: Dict[str, str],
    calculation_id: str,
    calculated_at: datetime.datetime,
) -> Dict[str, Any]:
    doc = {key: _to_bson(value) for key, value in financials.items()}
    doc.update(
        {
            "deal_id": deal["deal_id"],
            "deal_owner": deal.get("deal_owner"),
            "customer_id": deal.get("customer_id"),
            "customer_name": deal.get("customer_name"),
            "close_date": _to_bson(
                datetime.date.fromisoformat(deal["close_date"])
                if deal.get("close_date")
                else None
            ),
            "plan_start_date": plan["start_date"],
            "plan_end_date": plan["end_date"],
            "_calculation_id": calculation_id,
            "calculated_at": calculated_at,
        }
    )
    return doc


def build_payout_docs(
    deal: Dict[str, Any],
    payouts: List[Dict[str, Any]],
    calculation_id: str,
    calculated_at: datetime.datetime,
) -> List[Dict[str, Any]]:
    """Stamp each payout with a deterministic `sequence` within its component."""
    counters: Dict[str, int] = defaultdict(int)
    docs = []
    for payout in payouts:
        component = payout["component"]
        doc = {key: _to_bson(value) for key, value in payout.items()}
        doc["deal_id"] = deal["deal_id"]
        doc["sequence"] = counters[component]
        counters[component] += 1
        doc["_calculation_id"] = calculation_id
        doc["calculated_at"] = calculated_at
        docs.append(doc)
    return docs


def persist_results(
    database,
    deal_ids: List[str],
    commission_docs: List[Dict[str, Any]],
    payout_docs: List[Dict[str, Any]],
    calculation_id: str,
) -> int:
    """
    Upsert commissions and payouts, then drop payouts of these deals that the
    latest run no longer produces. Returns the number of stale payouts removed.
    Re-running with the same input never creates duplicates.
    """
    if commission_docs:
        database.commissions.bulk_write(
            [
                ReplaceOne({"deal_id": doc["deal_id"]}, doc, upsert=True)
                for doc in commission_docs
            ]
        )
    if payout_docs:
        database.payouts.bulk_write(
            [
                ReplaceOne(
                    {
                        "deal_id": doc["deal_id"],
                        "component": doc["component"],
                        "sequence": doc["sequence"],
                    },
                    doc,
                    upsert=True,
                )
                for doc in payout_docs
            ]
        )
    if not deal_ids:
        return 0
    removed = database.payouts.delete_many(
        {"deal_id": {"$in": deal_ids}, "_calculation_id": {"$ne": calculation_id}}
    )
    return removed.deleted_count


def run_calculations(
    database,
    plan: Optional[Dict[str, str]] = None,
    deal_ids: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """
    Calculate and persist commissions/payouts for stored deals
    (all deals, or only `deal_ids`). Safe to run any number of times.
    """
    plan = plan or DEFAULT_PLAN
    calculation_id = str(uuid.uuid4())
    calculated_at = _utcnow()

    # Normalize deal_ids: None or empty iterable means calculate ALL stored deals.
    clean_deal_ids = None
    if deal_ids is not None:
        clean_deal_ids = [
            str(d).strip() for d in deal_ids if d is not None and str(d).strip()
        ]
        if not clean_deal_ids:
            clean_deal_ids = None

    query: Dict[str, Any] = {}
    if clean_deal_ids is not None:
        query = {"deal_id": {"$in": clean_deal_ids}}

    processed_ids: List[str] = []
    commission_docs: List[Dict[str, Any]] = []
    payout_docs: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    for stored in database.deals.find(query, {"_id": 0}):
        deal_id = stored.get("deal_id")
        try:
            deal = to_engine_deal(stored)
            financials, payouts = calculate_deal(deal, plan)
            commission_docs.append(
                build_commission_doc(deal, financials, plan, calculation_id, calculated_at)
            )
            payout_docs.extend(build_payout_docs(deal, payouts, calculation_id, calculated_at))
            processed_ids.append(deal_id)
        except Exception as exc:  # a failing deal must not block the others
            errors.append({"deal_id": str(deal_id), "error": str(exc)})

    removed = persist_results(
        database, processed_ids, commission_docs, payout_docs, calculation_id
    )

    return {
        "calculation_id": calculation_id,
        "plan": plan,
        "deals_calculated": len(processed_ids),
        "deals_failed": len(errors),
        "payouts_generated": len(payout_docs),
        "stale_payouts_removed": removed,
        "errors": errors,
        "totals": {
            "deals": database.deals.count_documents({}),
            "commissions": database.commissions.count_documents({}),
            "payouts": database.payouts.count_documents({}),
        },
    }
