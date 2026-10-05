"""
Tests for the MongoDB calculation pipeline (import -> calculate -> persist).

Uses an in-memory mongomock database; Atlas is never touched.
The calculation engine and tests/fixtures/ are read-only here.
"""

import datetime
import json
from pathlib import Path

import mongomock
import pytest
from pymongo.errors import DuplicateKeyError

from backend.app.db.indexes import ensure_indexes
from backend.app.services.commission_runner import (
    calculate_deal,
    run_calculations,
    to_engine_deal,
)
from backend.app.services.deal_import import import_deals

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"

# DL-265126 from the golden workbook: Direct, in plan, annual subscription.
DEAL_ID = "DL-265126"


def raw_deal(**overrides):
    """A raw deal row using the verbatim Excel headers."""
    row = {
        "Deal ID": DEAL_ID,
        "Customer ID": "CUST-10389",
        "Customer Name": "Riverbend Concrete Ltd.",
        "Deal Name": "Riverbend Concrete Ltd. - New Deal",
        "Deal Type": "New",
        "Deal Owner": "Ethan Kowalski",
        "Lead Source": "Organic",
        "Partner Name": None,
        "Close Date": "2026-07-05T00:00:00",
        "Deal Status": "Closed Won",
        "Cancellation Date": None,
        "Total Contract Value - Year 1 (USD)": 68600,
        "Implementation Fee (USD)": 9000,
        "Implementation Payment Terms": "100% at signing",
        "Billing Type": "Annual Subscription",
        "Go-Live Date": "2026-10-09T00:00:00",
        "Invoice Payment Terms (Working Days)": 15,
    }
    row.update(overrides)
    return row


@pytest.fixture
def database():
    database = mongomock.MongoClient()["lumberfi_test"]
    ensure_indexes(database)
    return database


@pytest.fixture
def loaded(database):
    """Database with the single DL-265126 deal imported."""
    import_deals(database, [raw_deal()], filename="test.csv")
    return database


# ── 1. importing deals ───────────────────────────────────────────────────────

def test_import_validates_normalizes_and_upserts(database):
    records = [
        raw_deal(),
        raw_deal(**{"Deal ID": "DL-2", "Implementation Fee (USD)": None}),
        raw_deal(**{"Deal ID": "DL-3", "Deal Name": None}),
        raw_deal(**{"Deal ID": "DL-4", "Close Date": "not-a-date"}),
        raw_deal(**{"Deal ID": "DL-5", "Implementation Fee (USD)": "abc"}),
    ]

    summary = import_deals(database, records, filename="deals.csv")

    assert summary["row_count"] == 5
    assert summary["successful_rows"] == 2
    assert summary["failed_rows"] == 3
    assert {e["row_index"] for e in summary["errors"]} == {2, 3, 4}
    assert database.deals.count_documents({}) == 2

    stored = database.deals.find_one({"deal_id": DEAL_ID})
    assert stored["tcv_year1"] == 68600.0
    assert stored["close_date"] == datetime.datetime(2026, 7, 5)
    assert stored["cancellation_date"] is None

    # blank implementation fee is normalised like the legacy parser: 0
    assert database.deals.find_one({"deal_id": "DL-2"})["implementation_fee"] == 0.0

    record = database.imports.find_one({"import_id": summary["import_id"]})
    assert record["filename"] == "deals.csv"
    assert record["successful_rows"] == 2


def test_reimporting_updates_instead_of_duplicating(loaded):
    import_deals(
        loaded,
        [raw_deal(**{"Total Contract Value - Year 1 (USD)": 70000})],
        filename="again.csv",
    )

    assert loaded.deals.count_documents({}) == 1
    assert loaded.deals.find_one({"deal_id": DEAL_ID})["tcv_year1"] == 70000.0
    assert loaded.imports.count_documents({}) == 2


def test_unique_indexes_reject_duplicates(loaded):
    run_calculations(loaded)
    with pytest.raises(DuplicateKeyError):
        loaded.deals.insert_one({"deal_id": DEAL_ID})
    with pytest.raises(DuplicateKeyError):
        loaded.commissions.insert_one({"deal_id": DEAL_ID})
    with pytest.raises(DuplicateKeyError):
        loaded.payouts.insert_one(
            {"deal_id": DEAL_ID, "component": "Advance", "sequence": 0}
        )


# ── 2. calculating a deal ────────────────────────────────────────────────────

def test_calculate_deal_reuses_validated_engine(loaded):
    stored = loaded.deals.find_one({"deal_id": DEAL_ID}, {"_id": 0})
    deal = to_engine_deal(stored)
    assert deal["close_date"] == "2026-07-05"  # engine expects ISO date strings

    financials, payouts = calculate_deal(deal)

    assert financials["in_plan"] is True
    assert financials["arr"] == 59600.0
    assert financials["channel"] == "Direct"
    assert financials["arr_commission"] == 5960.0
    assert financials["implementation_commission"] == 900.0
    assert [p["component"] for p in payouts] == ["Advance", "Implementation", "Balance"]


# ── 3. persisting commission ─────────────────────────────────────────────────

def test_commission_is_persisted_per_deal(loaded):
    result = run_calculations(loaded)

    assert result["deals_calculated"] == 1
    assert result["deals_failed"] == 0
    commissions = list(loaded.commissions.find({}, {"_id": 0}))
    assert len(commissions) == 1
    commission = commissions[0]
    assert commission["deal_id"] == DEAL_ID
    assert commission["deal_owner"] == "Ethan Kowalski"
    assert commission["arr"] == 59600.0
    assert commission["arr_commission"] == 5960.0
    assert commission["implementation_commission"] == 900.0
    assert commission["in_plan"] is True
    assert commission["plan_start_date"] == "2026-07-01"


# ── 4. persisting payouts ────────────────────────────────────────────────────

def test_payouts_are_persisted_with_date_only_values(loaded):
    run_calculations(loaded)

    payouts = {
        p["component"]: p for p in loaded.payouts.find({"deal_id": DEAL_ID}, {"_id": 0})
    }
    assert set(payouts) == {"Advance", "Implementation", "Balance"}

    assert payouts["Advance"]["amount"] == 1490.0
    assert payouts["Advance"]["payout_date"] == datetime.datetime(2026, 8, 10)
    assert payouts["Implementation"]["amount"] == 900.0
    assert payouts["Implementation"]["payout_date"] == datetime.datetime(2026, 8, 17)
    assert payouts["Balance"]["amount"] == 4470.0
    assert payouts["Balance"]["payout_date"] == datetime.datetime(2026, 8, 28)
    assert payouts["Balance"]["collection_date"] == datetime.datetime(2026, 7, 24)
    assert all(p["sequence"] == 0 for p in payouts.values())


# ── 5. re-running without duplicates ─────────────────────────────────────────

def test_rerun_does_not_create_duplicates(loaded):
    first = run_calculations(loaded)
    counts = (
        loaded.deals.count_documents({}),
        loaded.commissions.count_documents({}),
        loaded.payouts.count_documents({}),
    )
    assert counts == (1, 1, 3)

    second = run_calculations(loaded)
    third = run_calculations(loaded)

    assert (
        loaded.deals.count_documents({}),
        loaded.commissions.count_documents({}),
        loaded.payouts.count_documents({}),
    ) == counts
    assert second["stale_payouts_removed"] == 0
    assert third["totals"] == {"deals": 1, "commissions": 1, "payouts": 3}
    # documents were refreshed in place by the latest run
    latest = third["calculation_id"]
    assert loaded.commissions.find_one({})["_calculation_id"] == latest
    assert {p["_calculation_id"] for p in loaded.payouts.find({})} == {latest}
    assert first["calculation_id"] != latest


def test_rerun_after_input_change_removes_stale_payouts(loaded):
    run_calculations(loaded)
    assert loaded.payouts.count_documents({"deal_id": DEAL_ID}) == 3

    # Deal moves outside the commission plan window -> no payouts any more.
    import_deals(loaded, [raw_deal(**{"Close Date": "2026-11-01"})], filename="fix.csv")
    result = run_calculations(loaded)

    assert result["stale_payouts_removed"] == 3
    assert loaded.payouts.count_documents({"deal_id": DEAL_ID}) == 0
    assert loaded.commissions.count_documents({}) == 1
    assert loaded.commissions.find_one({"deal_id": DEAL_ID})["in_plan"] is False


def test_run_can_be_scoped_to_deal_ids(database):
    import_deals(
        database,
        [raw_deal(), raw_deal(**{"Deal ID": "DL-OTHER"})],
        filename="two.csv",
    )

    result = run_calculations(database, deal_ids=["DL-OTHER"])

    assert result["deals_calculated"] == 1
    assert database.commissions.count_documents({"deal_id": "DL-OTHER"}) == 1
    assert database.commissions.count_documents({"deal_id": DEAL_ID}) == 0


# ── admin endpoint ───────────────────────────────────────────────────────────

def test_admin_calculate_endpoint(loaded):
    from fastapi import HTTPException

    from backend.app.api.calculations import CalculationRequest, calculate_commissions

    first = calculate_commissions(CalculationRequest(), loaded)
    again = calculate_commissions(None, loaded)

    assert first["deals_calculated"] == 1
    assert first["payouts_generated"] == 3
    assert again["deals_calculated"] == 1
    assert again["payouts_generated"] == 3
    assert again["stale_payouts_removed"] == 0
    assert again["totals"] == {"deals": 1, "commissions": 1, "payouts": 3}

    with pytest.raises(HTTPException) as half:
        calculate_commissions(
            CalculationRequest(plan_start_date=datetime.date(2026, 7, 1)), loaded
        )
    assert half.value.status_code == 422

    # a plan window that excludes the deal changes the result, same endpoint
    shifted = calculate_commissions(
        CalculationRequest(
            plan_start_date=datetime.date(2026, 10, 1),
            plan_end_date=datetime.date(2026, 12, 31),
        ),
        loaded,
    )
    assert shifted["stale_payouts_removed"] == 3
    assert loaded.commissions.find_one({"deal_id": DEAL_ID})["in_plan"] is False


# ── end-to-end against the golden workbook fixtures (read-only) ──────────────

def test_pipeline_reproduces_golden_fixtures(database):
    deals_path = FIXTURES / "deals.json"
    calcs_path = FIXTURES / "calculations.json"
    payouts_path = FIXTURES / "payouts.json"
    if not (deals_path.exists() and calcs_path.exists() and payouts_path.exists()):
        pytest.skip("Golden fixtures not generated yet")

    deals = json.loads(deals_path.read_text())
    calcs = {c["Deal ID"]: c for c in json.loads(calcs_path.read_text())}
    payouts = json.loads(payouts_path.read_text())

    summary = import_deals(database, deals, filename="golden.json")
    assert summary["failed_rows"] == 0, summary["errors"]

    result = run_calculations(database)
    assert result["deals_failed"] == 0, result["errors"]

    for deal_id, expected in calcs.items():
        commission = database.commissions.find_one({"deal_id": deal_id})
        assert commission["arr"] == expected["ARR"], deal_id
        assert commission["arr_commission"] == expected["ARR Commission"], deal_id
        assert (
            commission["implementation_commission"] == expected["Implementation Commission"]
        ), deal_id

    assert database.payouts.count_documents({}) == len(payouts)

    # idempotent on the full dataset too
    run_calculations(database)
    assert database.commissions.count_documents({}) == len(deals)
    assert database.payouts.count_documents({}) == len(payouts)


# ── 7. Excel (XLSX) and CSV import pipeline tests ───────────────────────────

def test_xlsx_import_selects_deals_sheet_only(database):
    """XLSX with multiple sheets must import ONLY the 'Deals' sheet."""
    import io
    import pandas as pd
    from fastapi import UploadFile
    from backend.app.api.admin import upload_deals

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame([{"Title": "Lumberfi", "Version": 1.0}]).to_excel(
            writer, sheet_name="Cover", index=False
        )
        pd.DataFrame([raw_deal()]).to_excel(
            writer, sheet_name="Deals", index=False
        )
        pd.DataFrame([{"User ID": "U-1", "Name": "Alice"}]).to_excel(
            writer, sheet_name="Users", index=False
        )
        pd.DataFrame([{"Calc ID": "C-1", "Val": 100}]).to_excel(
            writer, sheet_name="Calculations", index=False
        )
        pd.DataFrame([{"Payout ID": "P-1", "Amount": 50}]).to_excel(
            writer, sheet_name="Payouts", index=False
        )
        pd.DataFrame([{"Key": "Rate", "Val": 0.1}]).to_excel(
            writer, sheet_name="Assumption", index=False
        )
    buffer.seek(0)

    upload_file = UploadFile(filename="multi_sheet.xlsx", file=buffer)
    response = upload_deals(file=upload_file, database=database)

    assert response["message"] == "Import completed"
    assert response["total_rows"] == 1
    assert response["successful_rows"] == 1
    assert response["failed_rows"] == 0
    assert response["errors"] == []
    assert database.deals.count_documents({}) == 1
    assert database.deals.find_one({})["deal_id"] == DEAL_ID


def test_xlsx_import_rejects_missing_deals_sheet(database):
    """XLSX without a 'Deals' sheet raises 400."""
    import io
    import pandas as pd
    from fastapi import HTTPException, UploadFile
    from backend.app.api.admin import upload_deals

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        pd.DataFrame([{"Title": "Cover Only"}]).to_excel(
            writer, sheet_name="Cover", index=False
        )
    buffer.seek(0)

    upload_file = UploadFile(filename="no_deals.xlsx", file=buffer)
    with pytest.raises(HTTPException) as exc_info:
        upload_deals(file=upload_file, database=database)
    assert exc_info.value.status_code == 400
    assert "Workbook does not contain a 'Deals' sheet" in exc_info.value.detail


def test_production_workbook_xlsx_imports_54_valid_deals(database):
    """Uploading the reference workbook imports exactly 54 valid deals."""
    from fastapi import UploadFile
    from backend.app.api.admin import upload_deals

    ref_workbook = Path(__file__).resolve().parents[2] / "data" / "reference" / "Lumberfi Commission Details.xlsx"
    if not ref_workbook.exists():
        pytest.skip("Reference workbook not found")

    with open(ref_workbook, "rb") as f:
        upload_file = UploadFile(filename=ref_workbook.name, file=f)
        response = upload_deals(file=upload_file, database=database)

    assert response["message"] == "Import completed"
    assert response["total_rows"] == 54
    assert response["successful_rows"] == 54
    assert response["failed_rows"] == 0
    assert response["errors"] == []
    assert database.deals.count_documents({}) == 54


def test_csv_import_accounting_dash_values(database):
    """CSV accounting dashes ('-') in numeric columns normalize to 0.0 without error."""
    import io
    from fastapi import UploadFile
    from backend.app.api.admin import upload_deals

    csv_content = (
        "Deal ID,Customer ID,Customer Name,Deal Name,Deal Type,Deal Owner,Lead Source,Partner Name,Close Date,Deal Status,Cancellation Date,Total Contract Value - Year 1 (USD),Implementation Fee (USD),Implementation Payment Terms,Billing Type,Go-Live Date,Invoice Payment Terms (Working Days)\n"
        "DL-DASH-1,C-1,Cust A,Deal A,New,Alice,Organic,,2026-07-26T00:00:00,Closed Won,,11200,-,100% at signing,Annual Subscription,2026-11-11T00:00:00,30\n"
        "DL-DASH-2,C-2,Cust B,Deal B,New,Bob,Organic,,2026-07-27T00:00:00,Closed Won,,12000, — ,100% at signing,Annual Subscription,2026-11-12T00:00:00,-\n"
    )
    upload_file = UploadFile(filename="accounting.csv", file=io.BytesIO(csv_content.encode("utf-8")))
    response = upload_deals(file=upload_file, database=database)

    assert response["successful_rows"] == 2
    assert response["failed_rows"] == 0
    assert response["errors"] == []

    d1 = database.deals.find_one({"deal_id": "DL-DASH-1"})
    assert d1["implementation_fee"] == 0.0
    d2 = database.deals.find_one({"deal_id": "DL-DASH-2"})
    assert d2["implementation_fee"] == 0.0
    assert d2["invoice_payment_terms_days"] == 0.0


def test_failed_csv_rows_expose_error_details(database):
    """Failed rows must expose row_number, deal_id, and clear error in response."""
    import io
    from fastapi import UploadFile
    from backend.app.api.admin import upload_deals

    csv_content = (
        "Deal ID,Customer ID,Customer Name,Deal Name,Deal Type,Deal Owner,Lead Source,Partner Name,Close Date,Deal Status,Cancellation Date,Total Contract Value - Year 1 (USD),Implementation Fee (USD),Implementation Payment Terms,Billing Type,Go-Live Date,Invoice Payment Terms (Working Days)\n"
        "DL-GOOD,C-1,Cust Good,Deal Good,New,Alice,Organic,,2026-07-26T00:00:00,Closed Won,,10000,1000,100% at signing,Annual Subscription,2026-11-11T00:00:00,30\n"
        "DL-BAD1,C-2,Cust Bad,,New,Bob,Organic,,2026-07-26T00:00:00,Closed Won,,10000,1000,100% at signing,Annual Subscription,2026-11-11T00:00:00,30\n"
        "DL-BAD2,C-3,Cust Bad2,Deal Bad2,New,Charlie,Organic,,invalid-date,Closed Won,,10000,1000,100% at signing,Annual Subscription,2026-11-11T00:00:00,30\n"
    )
    upload_file = UploadFile(filename="mixed.csv", file=io.BytesIO(csv_content.encode("utf-8")))
    response = upload_deals(file=upload_file, database=database)

    assert response["total_rows"] == 3
    assert response["successful_rows"] == 1
    assert response["failed_rows"] == 2
    assert len(response["errors"]) == 2

    err1 = response["errors"][0]
    assert err1["row_number"] == 3
    assert err1["deal_id"] == "DL-BAD1"
    assert "Missing deal_name" in err1["error"]

    err2 = response["errors"][1]
    assert err2["row_number"] == 4
    assert err2["deal_id"] == "DL-BAD2"
    assert "Invalid date format" in err2["error"]


# ── 8. Calculation response bookkeeping and counter tests ─────

def test_calculate_counters_full_calculation_with_empty_or_none_deal_ids(database):
    """Full calculation with deal_ids=None, [], or ['  '] calculates all deals."""
    from backend.app.api.calculations import CalculationRequest, calculate_commissions

    import_deals(
        database,
        [
            raw_deal(**{"Deal ID": "DL-COUNT-1"}),
            raw_deal(**{"Deal ID": "DL-COUNT-2"}),
        ],
        filename="counts.csv",
    )

    # 1. No deal_ids specified (None)
    res_none = calculate_commissions(CalculationRequest(), database)
    assert res_none["deals_calculated"] == 2
    assert res_none["deals_failed"] == 0
    assert res_none["payouts_generated"] == 6
    assert res_none["stale_payouts_removed"] == 0
    assert res_none["totals"] == {"deals": 2, "commissions": 2, "payouts": 6}

    # 2. Empty list [] in request body (e.g. from Swagger UI)
    res_empty = calculate_commissions(CalculationRequest(deal_ids=[]), database)
    assert res_empty["deals_calculated"] == 2
    assert res_empty["deals_failed"] == 0
    assert res_empty["payouts_generated"] == 6
    assert res_empty["stale_payouts_removed"] == 0

    # 3. Whitespace-only string in list
    res_space = calculate_commissions(CalculationRequest(deal_ids=["   "]), database)
    assert res_space["deals_calculated"] == 2
    assert res_space["deals_failed"] == 0
    assert res_space["payouts_generated"] == 6
    assert res_space["stale_payouts_removed"] == 0


def test_calculate_counters_scoped_and_rerun(database):
    """Scoped calculation computes only requested deals; rerun maintains counts."""
    from backend.app.api.calculations import CalculationRequest, calculate_commissions

    import_deals(
        database,
        [
            raw_deal(**{"Deal ID": "DL-SCOPE-1"}),
            raw_deal(**{"Deal ID": "DL-SCOPE-2"}),
        ],
        filename="scope.csv",
    )

    # Scoped run on only DL-SCOPE-1
    res_scoped = calculate_commissions(
        CalculationRequest(deal_ids=["DL-SCOPE-1"]), database
    )
    assert res_scoped["deals_calculated"] == 1
    assert res_scoped["deals_failed"] == 0
    assert res_scoped["payouts_generated"] == 3
    assert res_scoped["stale_payouts_removed"] == 0
    assert res_scoped["totals"] == {"deals": 2, "commissions": 1, "payouts": 3}

    # Rerunning the full dataset recalculates both deals and generates all payouts
    res_full = calculate_commissions(CalculationRequest(), database)
    assert res_full["deals_calculated"] == 2
    assert res_full["deals_failed"] == 0
    assert res_full["payouts_generated"] == 6
    assert res_full["stale_payouts_removed"] == 0
    assert res_full["totals"] == {"deals": 2, "commissions": 2, "payouts": 6}

    # Rerunning a second time on the same dataset
    res_rerun = calculate_commissions(CalculationRequest(), database)
    assert res_rerun["deals_calculated"] == 2
    assert res_rerun["deals_failed"] == 0
    assert res_rerun["payouts_generated"] == 6
    assert res_rerun["stale_payouts_removed"] == 0
    assert res_rerun["totals"] == {"deals": 2, "commissions": 2, "payouts": 6}


def test_calculate_counters_failed_deal(database):
    """When a deal fails during calculation, deals_failed is incremented and error recorded."""
    from backend.app.api.calculations import CalculationRequest, calculate_commissions

    import_deals(
        database,
        [raw_deal(**{"Deal ID": "DL-GOOD-1"})],
        filename="good.csv",
    )
    # Insert a corrupt deal record directly in MongoDB that triggers calculation failure
    database.deals.insert_one(
        {
            "deal_id": "DL-BROKEN",
            "deal_name": "Broken Deal",
            "close_date": "not-a-valid-date",
            "tcv_year1": 50000.0,
            "implementation_fee": 5000.0,
        }
    )

    res = calculate_commissions(CalculationRequest(), database)
    assert res["deals_calculated"] == 1
    assert res["deals_failed"] == 1
    assert len(res["errors"]) == 1
    assert res["errors"][0]["deal_id"] == "DL-BROKEN"
    assert res["totals"]["deals"] == 2
    assert res["totals"]["commissions"] == 1
