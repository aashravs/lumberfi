"""
User service: seeding initial demo users from reference workbook and managing users.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from pymongo import UpdateOne

from backend.app.core.config import settings
from backend.app.core.security import hash_password

REFERENCE_WORKBOOK = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "reference"
    / "Lumberfi Commission Details.xlsx"
)

# Additional deal owners present in Deals sheet to ensure all 7 AEs have accounts
DEAL_OWNERS = [
    ("sofia.brandt@lumberfi.com", "Sofia Brandt", "AE", "manager@gmail.com"),
    ("liam.ortega@lumberfi.com", "Liam Ortega", "AE", "manager@gmail.com"),
    ("marcus.delaney@lumberfi.com", "Marcus Delaney", "AE", "manager@gmail.com"),
    ("daniel.osei@lumberfi.com", "Daniel Osei", "AE", "manager@gmail.com"),
    ("aisha.morrow@lumberfi.com", "Aisha Morrow", "AE", "manager@gmail.com"),
    ("hannah.whitfield@lumberfi.com", "Hannah Whitfield", "AE", "manager@gmail.com"),
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def seed_users(
    database,
    default_password: Optional[str] = None,
    workbook_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Seed initial users from the 'Users' sheet of the reference workbook.
    Idempotent: uses upsert on email. Does not duplicate users.
    """
    password = default_password or settings.DEFAULT_DEMO_PASSWORD
    hashed_pwd = hash_password(password)
    path = workbook_path or REFERENCE_WORKBOOK

    users_to_seed: List[Dict[str, Any]] = []

    # 1. Read from Users sheet if workbook exists
    if path.exists():
        try:
            excel = pd.ExcelFile(path)
            if "Users" in excel.sheet_names:
                df = pd.read_excel(excel, sheet_name="Users")
                df = df.astype(object).where(df.notna(), None)
                for r in df.to_dict(orient="records"):
                    email = str(r.get("Email", "")).strip().lower()
                    if not email or email == "none":
                        continue
                    name = str(r.get("Name", "")).strip()
                    raw_role = str(r.get("Role", "AE")).strip()
                    # Normalize role to canonical capitalization: Admin, Manager, AE
                    role_map = {"admin": "Admin", "manager": "Manager", "ae": "AE"}
                    role = role_map.get(raw_role.lower(), raw_role)

                    mgr = r.get("Manager Email")
                    mgr_email = str(mgr).strip().lower() if mgr and str(mgr).strip().lower() != "none" else None
                    # Normalize manager@test.com to manager@gmail.com for consistency with seeded manager
                    if mgr_email == "manager@test.com":
                        mgr_email = "manager@gmail.com"

                    active = bool(r.get("Active", True))

                    users_to_seed.append(
                        {
                            "email": email,
                            "name": name,
                            "role": role,
                            "manager_email": mgr_email,
                            "active": active,
                        }
                    )
        except Exception:
            pass

    # Fallback / baseline users if workbook didn't load them
    if not users_to_seed:
        users_to_seed = [
            {
                "email": "aashrav04@gmail.com",
                "name": "Ethan Kowalski",
                "role": "AE",
                "manager_email": "manager@gmail.com",
                "active": True,
            },
            {
                "email": "ae2@test.com",
                "name": "Test AE 2",
                "role": "AE",
                "manager_email": "manager@gmail.com",
                "active": True,
            },
            {
                "email": "manager@gmail.com",
                "name": "Test Manager",
                "role": "Manager",
                "manager_email": None,
                "active": True,
            },
            {
                "email": "admin@gmail.com",
                "name": "Aashrav",
                "role": "Admin",
                "manager_email": None,
                "active": True,
            },
        ]

    # Also ensure manager@test.com alias exists as Manager
    users_to_seed.append(
        {
            "email": "manager@test.com",
            "name": "Test Manager (Alt)",
            "role": "Manager",
            "manager_email": None,
            "active": True,
        }
    )

    # 2. Add deal owners so all AEs from Deals sheet have accounts
    existing_emails = {u["email"] for u in users_to_seed}
    for email, name, role, mgr in DEAL_OWNERS:
        if email not in existing_emails:
            users_to_seed.append(
                {
                    "email": email,
                    "name": name,
                    "role": role,
                    "manager_email": mgr,
                    "active": True,
                }
            )

    # 3. Upsert into database
    operations = []
    now = _utcnow()
    for user_doc in users_to_seed:
        # Don't overwrite existing hashed_password if user already has one, unless seeding new
        operations.append(
            UpdateOne(
                {"email": user_doc["email"]},
                {
                    "$set": {
                        "name": user_doc["name"],
                        "role": user_doc["role"],
                        "manager_email": user_doc["manager_email"],
                        "active": user_doc["active"],
                        "updated_at": now,
                    },
                    "$setOnInsert": {
                        "email": user_doc["email"],
                        "hashed_password": hashed_pwd,
                        "created_at": now,
                    },
                },
                upsert=True,
            )
        )

    if operations:
        database.users.bulk_write(operations, ordered=False)

    return {
        "seeded_count": len(users_to_seed),
        "total_users": database.users.count_documents({}),
    }
