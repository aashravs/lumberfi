"""
normalize_deal.py
-----------------
Maps a raw deal dict (verbatim Excel column headers, as extracted into
tests/fixtures/deals.json) to the internal canonical snake_case schema
consumed by calculate_financials() and generate_payouts().

Pipeline:
    Raw Excel dict  ->  normalize_deal()  ->  Internal canonical dict
                                          ->  calculate_financials()
                                          ->  generate_payouts()

This mirrors the inline normalisation that the legacy Apps Script performs
inside getDeals() (code.gs lines 13-31), where row[11] becomes `tcv`,
row[12] becomes `implementationFee`, etc.

Rules
-----
- Numeric fields: coerce to float; treat empty-string / None as 0.0.
- Date fields:    keep as-is (ISO strings); engine's parse_date() handles them.
- String fields:  strip whitespace; treat None / empty as None.
- Do NOT change business logic or golden fixture values.
"""

from typing import Any, Dict, Optional


def _parse_number(value: Any, default: float = 0.0) -> float:
    """
    Coerce a cell value to float.

    Handles:
    - Already a numeric type (int / float)
    - A string like "$1,234.56" or "1234" (strip currency symbols / commas)
    - None, empty string, whitespace -> default
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(",", "").replace("$", "")
    if s in ("", "-", "—", "–", "N/A", "n/a", "NA"):
        return default
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1].strip()
    try:
        return float(s)
    except ValueError:
        return default


def _parse_string(value: Any) -> Optional[str]:
    """Return stripped string or None for blank/null values."""
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def _parse_date(value: Any) -> Optional[str]:
    """
    Keep date values as-is (ISO strings or None).
    The calculation engine's parse_date() handles the final conversion.
    Returns None for blank/null values.
    """
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


def normalize_deal(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a raw Excel-header deal dict into the internal canonical schema.

    Raw key                                     -> Canonical key
    ------------------------------------------- ----------------------------
    "Deal ID"                                   -> deal_id
    "Customer ID"                               -> customer_id
    "Customer Name"                             -> customer_name
    "Deal Name"                                 -> deal_name
    "Deal Type"                                 -> deal_type
    "Deal Owner"                                -> deal_owner
    "Lead Source"                               -> lead_source
    "Partner Name"                              -> partner_name
    "Close Date"                                -> close_date
    "Deal Status"                               -> deal_status
    "Cancellation Date"                         -> cancellation_date
    "Total Contract Value - Year 1 (USD)"       -> tcv_year1
    "Implementation Fee (USD)"                  -> implementation_fee
    "Implementation Payment Terms"              -> implementation_payment_terms
    "Billing Type"                              -> billing_type
    "Go-Live Date"                              -> go_live_date
    "Invoice Payment Terms (Working Days)"      -> invoice_payment_terms_days

    Parameters
    ----------
    raw : dict
        A single deal record with verbatim Excel column headers.

    Returns
    -------
    dict
        A deal record using the internal canonical snake_case keys.
    """
    return {
        "deal_id":                      _parse_string(raw.get("Deal ID")),
        "customer_id":                  _parse_string(raw.get("Customer ID")),
        "customer_name":                _parse_string(raw.get("Customer Name")),
        "deal_name":                    _parse_string(raw.get("Deal Name")),
        "deal_type":                    _parse_string(raw.get("Deal Type")),
        "deal_owner":                   _parse_string(raw.get("Deal Owner")),
        "lead_source":                  _parse_string(raw.get("Lead Source")),
        "partner_name":                 _parse_string(raw.get("Partner Name")),
        "close_date":                   _parse_date(raw.get("Close Date")),
        "deal_status":                  _parse_string(raw.get("Deal Status")),
        "cancellation_date":            _parse_date(raw.get("Cancellation Date")),
        "tcv_year1":                    _parse_number(raw.get("Total Contract Value - Year 1 (USD)")),
        "implementation_fee":           _parse_number(raw.get("Implementation Fee (USD)")),
        "implementation_payment_terms": _parse_string(raw.get("Implementation Payment Terms")),
        "billing_type":                 _parse_string(raw.get("Billing Type")),
        "go_live_date":                 _parse_date(raw.get("Go-Live Date")),
        "invoice_payment_terms_days":   _parse_number(
                                            raw.get("Invoice Payment Terms (Working Days)"),
                                            default=0.0
                                        ),
    }
