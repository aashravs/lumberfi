# Regression Analysis

## Known Discrepancies & Gotchas

While mapping the expected `Calculations` and `Payouts` against the legacy `Code.gs` logic, several logical discrepancies surface due to the migration from Google Apps Script (JavaScript) to Python. These must be handled carefully to preserve the Golden Output.

### 1. Date Month Indexing
**Relevant Function**: `calculateFinancials()`, `get_last_friday_of_month()`
**Issue**: JavaScript's `Date` constructor uses **0-indexed months** (`0` = January, `11` = December). 
- In `Code.gs`: `new Date(2026, 6, 1)` actually represents **July 1, 2026**.
- **Python Implication**: If we naively port this to Python as `datetime.date(2026, 6, 1)`, it will evaluate to **June 1, 2026**, failing the regression tests for Q3 boundaries.
- **Action**: We must use 1-indexed months in Python, shifting all hardcoded Apps Script month integers by +1.

### 2. Null/Blank Math Evaluation
**Relevant Function**: `calculateFinancials()`
**Issue**: When the Excel sheet has a blank `Implementation Fee` (which we parsed as `None` in Python), JavaScript coerces `undefined`/`null`/`""` to `0` during subtraction:
- `ARR = TCV - ImplementationFee` (e.g. `100000 - undefined` evaluates to `NaN` in strict JS, but `100000 - ""` or `100000 - null` evaluates to `100000`).
- **Python Implication**: `100000 - None` throws a `TypeError`.
- **Action**: Python must explicitly coalesce `None` to `0.0` before performing financial arithmetic.

### 3. Date Shifting on Weekends
**Relevant Function**: `addWorkingDays(date, 0)`
**Issue**: The legacy `addWorkingDays` function initializes `daysAdded = 0` and loops `while (daysAdded < workingDays)`. 
- If `workingDays` is `0`, the loop never executes, and the function returns the *exact original date*—even if that original date is a Saturday or Sunday.
- **Python Implication**: Standard business-day libraries (like `pandas.tseries.offsets.BusinessDay`) typically snap a weekend date to a Friday or Monday even if adding `0` days. 
- **Action**: We must preserve the legacy bug/quirk where `addWorkingDays(date, 0)` does not snap weekends, to ensure the regression oracle matches perfectly.

### 4. Floating Point Precision
**Relevant Function**: `calculateFinancials()`
**Issue**: JavaScript uses double-precision floats for all numbers. Simple percentages (e.g. `0.10 * 85000`) might yield floating point artifacts in JS, which Excel obscures through formatting.
- **Action**: Python tests will use a tolerance (`abs(a - b) < 1e-9`) instead of strict equality to avoid failing on negligible precision differences.

*(Note: Specific Deal ID discrepancies will be appended here once the Python calculation engine executes its first pass against the complete `deals.json` fixture).*
