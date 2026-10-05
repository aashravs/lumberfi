import datetime
from typing import Dict, Any, List
from backend.app.services.dates import (
    add_working_days,
    move_to_monday_if_weekend,
    get_next_month_day,
    get_last_friday_of_month,
)

def parse_date(date_str) -> datetime.date:
    if not date_str:
        return None
    # ISO string from JSON
    if isinstance(date_str, str):
        return datetime.datetime.fromisoformat(date_str.replace('Z', '')).date()
    return date_str

def calculate_financials(deal: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    # 1. Check in_plan
    close_date = parse_date(deal.get("close_date"))
    start_date = parse_date(plan["start_date"])
    end_date = parse_date(plan["end_date"])
    
    in_plan = False
    if close_date and start_date <= close_date <= end_date:
        in_plan = True
        
    # 2. ARR = TCV - Implementation Fee
    tcv = deal.get("tcv_year1")
    if tcv is None:
        tcv = 0.0
    impl_fee = deal.get("implementation_fee")
    if impl_fee is None:
        impl_fee = 0.0
        
    arr = tcv - impl_fee
    
    # 3. Channel & ARR Commission Rate
    lead_source = deal.get("lead_source")
    if lead_source == "Partnership":
        channel = "Partner"
        arr_rate = 0.05
    else:
        channel = "Direct"
        arr_rate = 0.10
        
    arr_commission = arr * arr_rate
    
    # 4. Implementation % & Commission Rate
    if tcv == 0:
        impl_pct = 0.0
    else:
        impl_pct = impl_fee / tcv
        
    if impl_pct <= 0.10:
        impl_rate = 0.0
    elif impl_pct <= 0.20:
        impl_rate = 0.10 if channel == "Direct" else 0.05
    else:
        impl_rate = 0.15 if channel == "Direct" else 0.10
        
    impl_commission = impl_fee * impl_rate
    
    return {
        "deal_id": deal.get("deal_id"),
        "in_plan": in_plan,
        "arr": arr,
        "channel": channel,
        "arr_commission_rate": arr_rate,
        "arr_commission": arr_commission,
        "implementation_percentage": impl_pct,
        "implementation_commission_rate": impl_rate,
        "implementation_commission": impl_commission
    }

def create_annual_payouts(deal: Dict[str, Any], financials: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not financials["in_plan"]:
        return []
        
    payouts = []
    close_date = parse_date(deal.get("close_date"))
    
    # Advance
    advance_amount = financials["arr_commission"] * 0.25
    advance_date = move_to_monday_if_weekend(get_next_month_day(close_date, 10))
    
    payouts.append({
        "deal_id": deal.get("deal_id"),
        "deal_owner": deal.get("deal_owner"),
        "component": "Advance",
        "payout_date": advance_date,
        "amount": advance_amount
    })
    
    # Implementation
    if financials["implementation_commission"] > 0:
        impl_amount = financials["implementation_commission"]
        signing_date = move_to_monday_if_weekend(get_next_month_day(close_date, 15))
        
        impl_terms = deal.get("implementation_payment_terms")
        if impl_terms == "100% at signing":
            payouts.append({
                "deal_id": deal.get("deal_id"),
                "deal_owner": deal.get("deal_owner"),
                "component": "Implementation",
                "payout_date": signing_date,
                "amount": impl_amount
            })
        elif impl_terms == "50% at signing / 50% at go-live":
            first_half = impl_amount * 0.50
            payouts.append({
                "deal_id": deal.get("deal_id"),
                "deal_owner": deal.get("deal_owner"),
                "component": "Implementation - Signing",
                "payout_date": signing_date,
                "amount": first_half
            })
            
            go_live_date = parse_date(deal.get("go_live_date"))
            if go_live_date:
                payment_terms = int(deal.get("invoice_payment_terms_days") or 0)
                go_live_collection = add_working_days(go_live_date, payment_terms)
                
                second_payout_year = go_live_collection.year
                second_payout_month = go_live_collection.month + 1
                if second_payout_month > 12:
                    second_payout_month = 1
                    second_payout_year += 1
                    
                second_payout_date = move_to_monday_if_weekend(
                    datetime.date(second_payout_year, second_payout_month, 15)
                )
                
                payouts.append({
                    "deal_id": deal.get("deal_id"),
                    "deal_owner": deal.get("deal_owner"),
                    "component": "Implementation - Go-Live",
                    "payout_date": second_payout_date,
                    "amount": first_half,
                    "collection_date": go_live_collection
                })
                
    # Balance
    billing_type = deal.get("billing_type")
    invoice_date = None
    if billing_type == "Annual Subscription":
        invoice_date = close_date
    elif billing_type == "Annual - Billed on Go-Live":
        invoice_date = parse_date(deal.get("go_live_date"))
        
    if invoice_date:
        payment_terms = int(deal.get("invoice_payment_terms_days") or 0)
        collection_date = add_working_days(invoice_date, payment_terms)
        
        balance_amount = financials["arr_commission"] * 0.75
        
        payout_year = collection_date.year
        payout_month = collection_date.month + 1
        if payout_month > 12:
            payout_month = 1
            payout_year += 1
            
        balance_date = get_last_friday_of_month(payout_year, payout_month)
        
        payouts.append({
            "deal_id": deal.get("deal_id"),
            "deal_owner": deal.get("deal_owner"),
            "component": "Balance",
            "payout_date": balance_date,
            "amount": balance_amount,
            "collection_date": collection_date
        })
        
    return payouts

def create_recurring_payouts(deal: Dict[str, Any], financials: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not financials["in_plan"]:
        return []
        
    billing_type = deal.get("billing_type")
    is_monthly = (billing_type == "Monthly - Billed on Go-Live")
    is_quarterly = (billing_type == "Quarterly - Billed on Go-Live")
    
    if not is_monthly and not is_quarterly:
        return []
        
    payouts = []
    close_date = parse_date(deal.get("close_date"))
    go_live_date = parse_date(deal.get("go_live_date"))
    if not go_live_date:
        return []
        
    # Advance
    advance_amount = financials["arr_commission"] * 0.25
    advance_date = move_to_monday_if_weekend(get_next_month_day(close_date, 10))
    payouts.append({
        "deal_id": deal.get("deal_id"),
        "deal_owner": deal.get("deal_owner"),
        "component": "Advance",
        "payout_date": advance_date,
        "amount": advance_amount
    })
    
    invoice_amount = (financials["arr"] / 12) if is_monthly else (financials["arr"] / 4)
    commission_per_invoice = invoice_amount * financials["arr_commission_rate"]
    
    remaining_recovery = advance_amount
    invoice_date = go_live_date
    cutoff_date = datetime.date(2027, 3, 31)
    payment_terms = int(deal.get("invoice_payment_terms_days") or 0)
    
    while invoice_date <= cutoff_date:
        collection_date = add_working_days(invoice_date, payment_terms)
        
        payout_year = collection_date.year
        payout_month = collection_date.month + 1
        if payout_month > 12:
            payout_month = 1
            payout_year += 1
            
        payout_date = get_last_friday_of_month(payout_year, payout_month)
        if payout_date > cutoff_date:
            break
            
        recovery = min(remaining_recovery, commission_per_invoice)
        net_payout = commission_per_invoice - recovery
        
        payouts.append({
            "deal_id": deal.get("deal_id"),
            "deal_owner": deal.get("deal_owner"),
            "component": "Monthly Commission" if is_monthly else "Quarterly Commission",
            "invoice_date": invoice_date,
            "collection_date": collection_date,
            "payout_date": payout_date,
            "gross_commission": commission_per_invoice,
            "recovered_advance": recovery,
            "amount": net_payout
        })
        
        remaining_recovery -= recovery
        
        # Next invoice
        if is_monthly:
            m = invoice_date.month + 1
            y = invoice_date.year
            if m > 12:
                m = 1
                y += 1
            invoice_date = datetime.date(y, m, invoice_date.day)
        else:
            m = invoice_date.month + 3
            y = invoice_date.year
            if m > 12:
                m -= 12
                y += 1
            invoice_date = datetime.date(y, m, invoice_date.day)
            
    return payouts

def create_cancellation_clawback(deal: Dict[str, Any], existing_payouts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cancel_str = deal.get("cancellation_date")
    if not cancel_str:
        return []
        
    cancellation_date = parse_date(cancel_str)
    go_live_date = parse_date(deal.get("go_live_date"))
    
    if go_live_date and cancellation_date >= go_live_date:
        return []
        
    clawback_amount = 0.0
    for p in existing_payouts:
        p_date = p["payout_date"]
        if p_date <= cancellation_date:
            if p["component"] in ["Advance", "Implementation", "Implementation - Signing"]:
                clawback_amount += p["amount"]
                
    if clawback_amount == 0:
        return []
        
    clawback_date = move_to_monday_if_weekend(get_next_month_day(cancellation_date, 10))
    return [{
        "deal_id": deal.get("deal_id"),
        "deal_owner": deal.get("deal_owner"),
        "component": "Cancellation Clawback",
        "payout_date": clawback_date,
        "amount": -clawback_amount
    }]

def generate_payouts(deal: Dict[str, Any], financials: Dict[str, Any]) -> List[Dict[str, Any]]:
    annual = create_annual_payouts(deal, financials)
    recurring = create_recurring_payouts(deal, financials)
    normal = annual + recurring
    
    cancel_str = deal.get("cancellation_date")
    if cancel_str:
        cancel_date = parse_date(cancel_str)
        go_live_date = parse_date(deal.get("go_live_date"))
        if go_live_date and cancel_date < go_live_date:
            normal = [p for p in normal if p["payout_date"] <= cancel_date]
            
    clawbacks = create_cancellation_clawback(deal, normal)
    return normal + clawbacks
