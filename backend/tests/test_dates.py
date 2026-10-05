import datetime
import pytest

def test_add_working_days():
    # In legacy: 
    # If workingDays is 0, it returns the exact same date (even if it's a weekend)
    # If workingDays > 0, it steps forward 1 day at a time, counting only Mon-Fri.
    from backend.app.services.dates import add_working_days
    
    # Thursday + 2 working days = Monday
    start = datetime.date(2026, 10, 1) # Thursday
    assert add_working_days(start, 2) == datetime.date(2026, 10, 5) # Monday
    
    # Sunday + 0 working days = Sunday (legacy quirk)
    start = datetime.date(2026, 10, 4) # Sunday
    assert add_working_days(start, 0) == datetime.date(2026, 10, 4)

def test_move_to_monday_if_weekend():
    # In legacy:
    # Saturday -> Monday (+2 days)
    # Sunday -> Monday (+1 day)
    from backend.app.services.dates import move_to_monday_if_weekend
    
    # Saturday -> Monday
    sat = datetime.date(2026, 10, 3)
    assert move_to_monday_if_weekend(sat) == datetime.date(2026, 10, 5)
    
    # Sunday -> Monday
    sun = datetime.date(2026, 10, 4)
    assert move_to_monday_if_weekend(sun) == datetime.date(2026, 10, 5)
    
    # Friday -> Friday
    fri = datetime.date(2026, 10, 2)
    assert move_to_monday_if_weekend(fri) == datetime.date(2026, 10, 2)

def test_get_next_month_day():
    # In legacy: getNextMonthDay(date, dayOfMonth)
    # new Date(date.getFullYear(), date.getMonth() + 1, dayOfMonth)
    from backend.app.services.dates import get_next_month_day
    
    base = datetime.date(2026, 10, 5)
    assert get_next_month_day(base, 10) == datetime.date(2026, 11, 10)
    
    # December -> January
    base = datetime.date(2026, 12, 1)
    assert get_next_month_day(base, 15) == datetime.date(2027, 1, 15)

def test_get_last_friday_of_month():
    # In legacy: getLastFridayOfMonth(year, month)
    # month is 0-indexed in JS! So get_last_friday_of_month(2026, 9) = Oct 2026 in JS, 
    # but in Python we should use 1-indexed months (10 for October).
    from backend.app.services.dates import get_last_friday_of_month
    
    # October 2026 last day is Oct 31 (Saturday)
    # Last Friday is Oct 30
    assert get_last_friday_of_month(2026, 10) == datetime.date(2026, 10, 30)
    
    # September 2026 last day is Sep 30 (Wednesday)
    # Last Friday is Sep 25
    assert get_last_friday_of_month(2026, 9) == datetime.date(2026, 9, 25)
