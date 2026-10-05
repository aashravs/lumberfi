from datetime import datetime
from zoneinfo import ZoneInfo
import json
import pytest
import os
from backend.app.services.normalize_deal import normalize_deal
from backend.app.services.calculation_engine import calculate_financials, generate_payouts


def parse_golden_payout_date(value):
    if not value:
        return None
    dt = datetime.fromisoformat(value).replace(
        tzinfo=ZoneInfo("America/Los_Angeles")
    )
    return dt.astimezone(
        ZoneInfo("Asia/Kolkata")
    ).date().isoformat()


@pytest.fixture
def fixtures():
    deals_path = "tests/fixtures/deals.json"
    payouts_path = "tests/fixtures/payouts.json"
    
    if not os.path.exists(deals_path) or not os.path.exists(payouts_path):
        pytest.skip("Fixtures not generated yet")
        
    with open(deals_path) as f:
        deals = json.load(f)
    with open(payouts_path) as f:
        payouts = json.load(f)
        
    # Group payouts by deal_id
    payouts_map = {}
    for p in payouts:
        deal_id = p["Deal ID"]
        if deal_id not in payouts_map:
            payouts_map[deal_id] = []
        payouts_map[deal_id].append(p)
        
    return deals, payouts_map

def test_generate_payouts(fixtures):
    deals, payouts_map = fixtures
    
    plan = {
        "start_date": "2026-07-01",
        "end_date": "2026-09-30"
    }
    
    for raw_deal in deals:
        expected_payouts = payouts_map.get(raw_deal["Deal ID"], [])

        # Normalise raw Excel headers -> internal canonical schema before
        # passing to the engine.  The engine itself stays clean.
        deal = normalize_deal(raw_deal)

        financials = calculate_financials(deal, plan)
        result_payouts = generate_payouts(deal, financials)
        
        assert len(result_payouts) == len(expected_payouts), \
            f"Payout count mismatch for {raw_deal['Deal ID']}: got {len(result_payouts)}, expected {len(expected_payouts)}"
        
        # Sort both by Payout Date and Component to ensure deterministic comparison
        result_payouts = sorted(result_payouts, key=lambda x: (str(x["payout_date"]), x["component"]))
        expected_payouts = sorted(expected_payouts, key=lambda x: (parse_golden_payout_date(x["Payout Date"]), x["Component"]))
        
        for res, exp in zip(result_payouts, expected_payouts):
            assert res["deal_owner"] == exp["Deal Owner"], \
                f"deal_owner mismatch for {raw_deal['Deal ID']}"
            assert res["component"] == exp["Component"], \
                f"component mismatch for {raw_deal['Deal ID']}"
            
            # Dates
            if exp.get("Invoice Date"):
                exp_invoice = parse_golden_payout_date(exp["Invoice Date"])
                assert str(res["invoice_date"]) == exp_invoice, \
                    f"invoice_date mismatch for {raw_deal['Deal ID']} / {res['component']}: got {res['invoice_date']}, expected {exp_invoice}"
            if exp.get("Collection Date"):
                exp_collection = parse_golden_payout_date(exp["Collection Date"])
                assert str(res["collection_date"]) == exp_collection, \
                    f"collection_date mismatch for {raw_deal['Deal ID']} / {res['component']}: got {res['collection_date']}, expected {exp_collection}"
                
            exp_payout = parse_golden_payout_date(exp["Payout Date"])
            assert str(res["payout_date"]) == exp_payout, \
                f"payout_date mismatch for {raw_deal['Deal ID']} / {res['component']}: got {res['payout_date']}, expected {exp_payout}"
            
            # Financials
            if exp.get("Gross Commission"):
                assert abs(res["gross_commission"] - exp["Gross Commission"]) < 1e-9, \
                    f"gross_commission mismatch for {raw_deal['Deal ID']}"
            if exp.get("Recovered Advance"):
                assert abs(res["recovered_advance"] - exp["Recovered Advance"]) < 1e-9, \
                    f"recovered_advance mismatch for {raw_deal['Deal ID']}"
                
            assert abs(res["amount"] - exp["Payout Amount"]) < 1e-9, \
                f"payout amount mismatch for {raw_deal['Deal ID']} / {res['component']}: got {res['amount']}, expected {exp['Payout Amount']}"

