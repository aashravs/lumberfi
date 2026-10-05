"""
Restore production MongoDB baseline to the original 54 deals from
data/reference/Lumberfi Commission Details.xlsx using the existing
import and calculation pipeline.
"""

import json
from pathlib import Path
import pandas as pd
from zoneinfo import ZoneInfo
from datetime import datetime

from backend.app.db.connection import db
from backend.app.services.deal_import import import_deals
from backend.app.services.commission_runner import run_calculations, DEFAULT_PLAN


def parse_golden_payout_date(value):
    if not value:
        return None
    dt = datetime.fromisoformat(value).replace(tzinfo=ZoneInfo("America/Los_Angeles"))
    return dt.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat()


def main():
    print("=== 1. Checking MongoDB Counts Before Restoration ===")
    deals_before = db.deals.count_documents({})
    commissions_before = db.commissions.count_documents({})
    payouts_before = db.payouts.count_documents({})
    dl_29999_in_deals = db.deals.count_documents({"deal_id": "DL-29999"})
    dl_29999_in_comm = db.commissions.count_documents({"deal_id": "DL-29999"})
    dl_29999_in_payouts = db.payouts.count_documents({"deal_id": "DL-29999"})
    print(f"Deals before: {deals_before}")
    print(f"Commissions before: {commissions_before}")
    print(f"Payouts before: {payouts_before}")
    print(f"DL-29999 exists: deals={dl_29999_in_deals}, comm={dl_29999_in_comm}, payouts={dl_29999_in_payouts}")

    print("\n=== 2. Removing DL-29999 if it exists ===")
    if dl_29999_in_deals > 0:
        res_d = db.deals.delete_one({"deal_id": "DL-29999"})
        print(f"Deleted from deals: {res_d.deleted_count}")
    if dl_29999_in_comm > 0:
        res_c = db.commissions.delete_one({"deal_id": "DL-29999"})
        print(f"Deleted from commissions: {res_c.deleted_count}")
    if dl_29999_in_payouts > 0:
        res_p = db.payouts.delete_many({"deal_id": "DL-29999"})
        print(f"Deleted from payouts: {res_p.deleted_count}")

    print("\n=== 3. Reading Deals Sheet from Reference Workbook ===")
    wb_path = Path("data/reference/Lumberfi Commission Details.xlsx")
    assert wb_path.exists(), f"Reference workbook not found: {wb_path}"
    excel = pd.ExcelFile(wb_path)
    assert "Deals" in excel.sheet_names, f"Deals sheet missing: {excel.sheet_names}"
    df = pd.read_excel(excel, sheet_name="Deals")
    df = df.astype(object).where(df.notna(), None)
    records = df.to_dict(orient="records")
    print(f"Found {len(records)} deal records in workbook 'Deals' sheet.")

    print("\n=== 4. Running Import Pipeline ===")
    summary = import_deals(db, records, filename="Lumberfi Commission Details.xlsx")
    print(f"Import summary: total_rows={summary['row_count']}, successful={summary['successful_rows']}, failed={summary['failed_rows']}")
    if summary["errors"]:
        print(f"Import errors: {summary['errors']}")

    print("\n=== 5. Running Commission Calculation Pipeline ===")
    calc_result = run_calculations(db, plan=DEFAULT_PLAN)
    print(f"Calculation result: calculated={calc_result['deals_calculated']}, failed={calc_result['deals_failed']}, payouts_generated={calc_result['payouts_generated']}, stale_removed={calc_result['stale_payouts_removed']}")
    print(f"Totals reported: {calc_result['totals']}")

    print("\n=== 6. Verifying MongoDB State After Restoration ===")
    deals_after = db.deals.count_documents({})
    commissions_after = db.commissions.count_documents({})
    payouts_after = db.payouts.count_documents({})
    dl_29999_after = db.deals.count_documents({"deal_id": "DL-29999"})
    print(f"Deals after: {deals_after}")
    print(f"Commissions after: {commissions_after}")
    print(f"Payouts after: {payouts_after}")
    print(f"DL-29999 in deals after: {dl_29999_after}")

    # Check duplicates
    deal_ids = list(db.deals.distinct("deal_id"))
    comm_deal_ids = list(db.commissions.distinct("deal_id"))
    print(f"Distinct deal_ids in deals: {len(deal_ids)}")
    print(f"Distinct deal_ids in commissions: {len(comm_deal_ids)}")

    # Calculate financial sums from MongoDB
    comm_docs = list(db.commissions.find({}, {"_id": 0}))
    payout_docs = list(db.payouts.find({}, {"_id": 0}))

    tot_arr_comm = sum(c.get("arr_commission", 0.0) for c in comm_docs)
    tot_impl_comm = sum(c.get("implementation_commission", 0.0) for c in comm_docs)
    tot_comm = round(tot_arr_comm + tot_impl_comm, 2)
    tot_payout = round(sum(p.get("amount", 0.0) for p in payout_docs), 2)

    print("\n=== 7. Financial Totals in MongoDB ===")
    print(f"Total Commission: ${tot_comm:,.2f} (Expected: $166,885.00)")
    print(f"ARR Commission: ${tot_arr_comm:,.2f} (Expected: $137,115.00)")
    print(f"Implementation Commission: ${tot_impl_comm:,.2f} (Expected: $29,770.00)")
    print(f"Total Payout: ${tot_payout:,.2f} (Expected: $157,980.00)")

    # Golden comparison
    print("\n=== 8. Golden Fixtures Parity Comparison ===")
    fixtures_dir = Path("tests/fixtures")
    golden_calcs = {c["Deal ID"]: c for c in json.loads((fixtures_dir / "calculations.json").read_text(encoding="utf-8"))}
    golden_payouts = json.loads((fixtures_dir / "payouts.json").read_text(encoding="utf-8"))

    comm_mismatches = 0
    for deal_id, golden in golden_calcs.items():
        doc = db.commissions.find_one({"deal_id": deal_id})
        if not doc:
            print(f"Missing commission doc for {deal_id}")
            comm_mismatches += 1
            continue
        if doc.get("arr") != golden.get("ARR"):
            print(f"Mismatch ARR {deal_id}: db={doc.get('arr')} vs golden={golden.get('ARR')}")
            comm_mismatches += 1
        if doc.get("arr_commission") != golden.get("ARR Commission"):
            print(f"Mismatch ARR comm {deal_id}: db={doc.get('arr_commission')} vs golden={golden.get('ARR Commission')}")
            comm_mismatches += 1
        if doc.get("implementation_commission") != golden.get("Implementation Commission"):
            print(f"Mismatch Impl comm {deal_id}: db={doc.get('implementation_commission')} vs golden={golden.get('Implementation Commission')}")
            comm_mismatches += 1

    payout_mismatches = 0
    # Match payouts by deal_id, component, sequence / amount
    # Payouts count:
    if len(payout_docs) != len(golden_payouts):
        print(f"Payout count mismatch: db={len(payout_docs)} vs golden={len(golden_payouts)}")
        payout_mismatches += abs(len(payout_docs) - len(golden_payouts))

    # Check total payout amount matches golden exactly
    golden_total_payout = sum(float(p.get("Payout Amount", 0)) for p in golden_payouts)
    if tot_payout != golden_total_payout:
        print(f"Total payout sum mismatch: db={tot_payout} vs golden={golden_total_payout}")
        payout_mismatches += 1

    print(f"Commission mismatches: {comm_mismatches}")
    print(f"Payout mismatches: {payout_mismatches}")

    # Assertions
    assert deals_after == 54, f"Expected 54 deals, got {deals_after}"
    assert commissions_after == 54, f"Expected 54 commissions, got {commissions_after}"
    assert payouts_after == 181, f"Expected 181 payouts, got {payouts_after}"
    assert dl_29999_after == 0, "DL-29999 still exists in deals!"
    assert tot_comm == 166885.0, f"Expected 166885.0 commission, got {tot_comm}"
    assert tot_arr_comm == 137115.0, f"Expected 137115.0 ARR comm, got {tot_arr_comm}"
    assert tot_impl_comm == 29770.0, f"Expected 29770.0 Impl comm, got {tot_impl_comm}"
    assert tot_payout == 157980.0, f"Expected 157980.0 payout, got {tot_payout}"
    assert comm_mismatches == 0, f"Expected 0 comm mismatches, got {comm_mismatches}"
    assert payout_mismatches == 0, f"Expected 0 payout mismatches, got {payout_mismatches}"

    print("\n[SUCCESS] BASELINE RESTORATION AND VERIFICATION COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
