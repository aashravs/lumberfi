import json
import pytest
import os
from backend.app.services.normalize_deal import normalize_deal
from backend.app.services.calculation_engine import calculate_financials

@pytest.fixture
def fixtures():
    deals_path = "tests/fixtures/deals.json"
    calc_path = "tests/fixtures/calculations.json"
    if not os.path.exists(deals_path) or not os.path.exists(calc_path):
        pytest.skip("Fixtures not generated yet")
        
    with open(deals_path) as f:
        deals = json.load(f)
    with open(calc_path) as f:
        calcs = json.load(f)
        
    calc_map = {c["Deal ID"]: c for c in calcs}
    return deals, calc_map

def test_calculate_financials(fixtures):
    deals, calc_map = fixtures
    
    plan = {
        "start_date": "2026-07-01",
        "end_date": "2026-09-30"
    }
    
    for raw_deal in deals:
        expected = calc_map.get(raw_deal["Deal ID"])
        if not expected:
            continue

        # Normalise raw Excel headers -> internal canonical schema before
        # passing to the engine.  This is the single translation point;
        # the engine itself stays clean.
        deal = normalize_deal(raw_deal)
        result = calculate_financials(deal, plan)
        
        deal_id = raw_deal["Deal ID"]

        assert result["arr"] == expected["ARR"], \
            f"ARR mismatch for {deal_id}: got {result['arr']}, expected {expected['ARR']}"
        assert result["in_plan"] == expected["In Plan"], \
            f"in_plan mismatch for {deal_id}"
        assert result["channel"] == expected["Channel"], \
            f"channel mismatch for {deal_id}"
        assert result["arr_commission_rate"] == expected["ARR Commission Rate"], \
            f"arr_commission_rate mismatch for {deal_id}"
        assert result["arr_commission"] == expected["ARR Commission"], \
            f"arr_commission mismatch for {deal_id}"
        assert abs(result["implementation_percentage"] - expected["Implementation Fee %"]) < 1e-9, \
            f"implementation_percentage mismatch for {deal_id}"
        assert result["implementation_commission_rate"] == expected["Implementation Commission Rate"], \
            f"implementation_commission_rate mismatch for {deal_id}"
        assert result["implementation_commission"] == expected["Implementation Commission"], \
            f"implementation_commission mismatch for {deal_id}"
