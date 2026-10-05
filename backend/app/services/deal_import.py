"""
Deal import service:  raw rows -> validate -> normalize -> upsert into MongoDB.

Pipeline for each uploaded row (verbatim Excel/CSV headers):

    raw row
      -> validate_raw_deal()      reject bad rows with a clear message
      -> normalize_deal()         raw headers -> canonical snake_case schema
      -> upsert into `deals`      keyed on deal_id (idempotent)

The header mapping lives only in normalize_deal(); nothing is duplicated here.
"""

import datetime
import uuid
from typing import Any, Dict, Iterable, List, Optional

from pymongo import UpdateOne

from backend.app.services.normalize_deal import normalize_deal

# Canonical date fields (stored in MongoDB as midnight datetimes).
DATE_FIELDS = ("close_date", "cancellation_date", "go_live_date")

# Raw headers that must be numeric when present.
_NUMERIC_HEADERS = (
    "Total Contract Value - Year 1 (USD)",
    "Implementation Fee (USD)",
    "Invoice Payment Terms (Working Days)",
)

# Raw headers that must be dates when present.
_DATE_HEADERS = ("Close Date", "Cancellation Date", "Go-Live Date")


class DealValidationError(ValueError):
    """Raised when an uploaded row cannot be imported."""


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    # NaN and NaT are the only values that are not equal to themselves.
    try:
        return bool(value != value)
    except Exception:
        return False


def parse_business_date(value: Any) -> Optional[datetime.date]:
    """Parse a date-like cell into a date, or None when blank."""
    if _is_blank(value):
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    text = str(value).strip()
    try:
        return datetime.datetime.fromisoformat(text.replace("Z", "")).date()
    except ValueError:
        pass
    try:
        from dateutil import parser as date_parser

        return date_parser.parse(text).date()
    except (ValueError, OverflowError):
        raise DealValidationError(f"Invalid date format: {value!r}")


def _check_numeric(header: str, value: Any) -> None:
    if _is_blank(value):
        return
    if isinstance(value, (int, float)):
        return
    cleaned = str(value).strip().replace(",", "").replace("$", "")
    if cleaned in ("", "-", "—", "–", "N/A", "n/a", "NA"):
        return
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1].strip()
    try:
        float(cleaned)
    except ValueError:
        raise DealValidationError(f"Invalid numeric value for '{header}': {value!r}")


def validate_raw_deal(raw: Dict[str, Any]) -> None:
    """
    Validate a raw row. normalize_deal() silently coerces bad numbers to 0.0,
    which would hide data problems in money fields, so we reject them here.
    """
    if _is_blank(raw.get("Deal ID")):
        raise DealValidationError("Missing deal_id")
    if _is_blank(raw.get("Deal Name")):
        raise DealValidationError("Missing deal_name")
    for header in _NUMERIC_HEADERS:
        _check_numeric(header, raw.get(header))
    for header in _DATE_HEADERS:
        parse_business_date(raw.get(header))


def build_deal_document(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Validate + normalize one raw row into the document stored in `deals`."""
    raw = {key: (None if _is_blank(value) else value) for key, value in raw.items()}
    validate_raw_deal(raw)
    deal = normalize_deal(raw)
    for field in DATE_FIELDS:
        parsed = parse_business_date(deal[field])
        deal[field] = (
            datetime.datetime.combine(parsed, datetime.time.min) if parsed else None
        )
    return deal


def import_deals(
    database,
    records: Iterable[Dict[str, Any]],
    filename: str,
    uploaded_by: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate, normalize and upsert deals; record the import in `imports`.

    Returns a summary including `deal_ids` (successfully imported deals).
    """
    records = list(records)
    import_id = str(uuid.uuid4())
    uploaded_at = _utcnow()

    operations: List[UpdateOne] = []
    deal_ids: List[str] = []
    errors: List[Dict[str, Any]] = []

    for index, raw in enumerate(records):
        try:
            doc = build_deal_document(raw)
            doc["_last_import_id"] = import_id
            doc["_updated_at"] = _utcnow()
            operations.append(
                UpdateOne({"deal_id": doc["deal_id"]}, {"$set": doc}, upsert=True)
            )
            deal_ids.append(doc["deal_id"])
        except Exception as exc:  # one bad row must not abort the file
            deal_id = raw.get("Deal ID") or raw.get("deal_id")
            errors.append({
                "row_number": index + 2,
                "row_index": index,
                "deal_id": deal_id,
                "error": str(exc),
            })

    if operations:
        # ordered so that, if a deal_id repeats in one file, the last row wins.
        database.deals.bulk_write(operations, ordered=True)

    summary = {
        "import_id": import_id,
        "uploaded_by": uploaded_by,
        "filename": filename,
        "uploaded_at": uploaded_at,
        "row_count": len(records),
        "successful_rows": len(operations),
        "failed_rows": len(errors),
        "errors": errors,
    }
    database.imports.insert_one(dict(summary))
    summary["deal_ids"] = deal_ids
    return summary
