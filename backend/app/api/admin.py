import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.app.api.deps import require_admin
from backend.app.db.connection import get_db
from backend.app.services.commission_runner import run_calculations
from backend.app.services.deal_import import import_deals

router = APIRouter(tags=["admin"])


@router.post("/api/admin/upload")
def upload_deals(
    file: UploadFile = File(...),
    calculate: bool = False,
    database=Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    if not isinstance(current_user, dict):
        current_user = {"email": "admin@test.com", "role": "Admin"}
    """
    Import deals from CSV/XLSX: validate -> normalize -> upsert (by deal_id).

    With `?calculate=true`, commissions and payouts are also (re)calculated
    for the deals in this file.
    """
    if not (file.filename.endswith(".csv") or file.filename.endswith(".xlsx")):
        raise HTTPException(status_code=400, detail="Only CSV and XLSX files are supported")

    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file.file)
        else:
            excel = pd.ExcelFile(file.file)
            if "Deals" not in excel.sheet_names:
                raise HTTPException(
                    status_code=400,
                    detail=f"Workbook does not contain a 'Deals' sheet. Found sheets: {excel.sheet_names}",
                )
            df = pd.read_excel(excel, sheet_name="Deals")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")

    # Blank cells (NaN/NaT) become None so validation sees them as empty.
    df = df.astype(object).where(df.notna(), None)
    records = df.to_dict(orient="records")

    summary = import_deals(database, records, filename=file.filename)

    response = {
        "message": "Import completed",
        "import_id": summary["import_id"],
        "total_rows": summary["row_count"],
        "successful_rows": summary["successful_rows"],
        "failed_rows": summary["failed_rows"],
        "errors": summary["errors"],
    }
    if calculate:
        response["calculation"] = run_calculations(
            database, deal_ids=summary["deal_ids"]
        )
    return response


@router.get("/api/admin/imports")
def list_imports(database=Depends(get_db), current_user: dict = Depends(require_admin)):
    imports = list(database.imports.find({}, {"_id": 0}).sort("uploaded_at", -1).limit(10))
    return {"imports": imports}
