import datetime

def add_working_days(date: datetime.date, working_days: int) -> datetime.date:
    """
    Legacy behavior:
    If workingDays is 0, returns the exact same date.
    Otherwise, steps forward 1 day at a time, counting only Mon-Fri.
    """
    result = date
    days_added = 0
    
    while days_added < working_days:
        result = result + datetime.timedelta(days=1)
        # Monday = 0, Sunday = 6 in Python
        if result.weekday() < 5:
            days_added += 1
            
    return result

def move_to_monday_if_weekend(date: datetime.date) -> datetime.date:
    """
    Saturday -> Monday (+2 days)
    Sunday -> Monday (+1 day)
    """
    if date.weekday() == 5: # Saturday
        return date + datetime.timedelta(days=2)
    elif date.weekday() == 6: # Sunday
        return date + datetime.timedelta(days=1)
    return date

def get_next_month_day(date: datetime.date, day_of_month: int) -> datetime.date:
    """
    Returns the `day_of_month` of the next month relative to `date`.
    """
    year = date.year
    month = date.month + 1
    if month > 12:
        month = 1
        year += 1
    return datetime.date(year, month, day_of_month)

def get_last_friday_of_month(year: int, month: int) -> datetime.date:
    """
    Returns the last Friday of the specified month/year.
    """
    # Find the last day of the month by getting the 1st of next month and subtracting 1 day
    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1
        
    last_day = datetime.date(next_year, next_month, 1) - datetime.timedelta(days=1)
    
    # Friday = 4. 
    # If last_day is Friday (4), we subtract 0
    # If last_day is Saturday (5), we subtract 1
    # If last_day is Sunday (6), we subtract 2
    # If last_day is Monday (0), we subtract 3
    days_back = (last_day.weekday() - 4) % 7
    return last_day - datetime.timedelta(days=days_back)
