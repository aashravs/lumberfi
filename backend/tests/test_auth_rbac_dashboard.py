"""
Tests for Phase 2: Authentication, Server-Side RBAC, and Dashboard APIs.
Uses an in-memory mongomock database with dependency_overrides.
"""

import io
import pytest
from fastapi.testclient import TestClient
import mongomock

from backend.app.main import app
from backend.app.db.connection import get_db
from backend.app.db.indexes import ensure_indexes
from backend.app.services.user_service import seed_users
from backend.app.services.deal_import import import_deals
from backend.app.services.commission_runner import run_calculations
from backend.tests.test_mongo_pipeline import raw_deal


@pytest.fixture
def mock_db():
    database = mongomock.MongoClient()["lumberfi_auth_test"]
    ensure_indexes(database)
    seed_users(database, default_password="demo123")

    # Import sample deals for multiple AEs:
    # Ethan Kowalski (AE under manager@gmail.com)
    # Sofia Brandt (AE under manager@gmail.com)
    # Test AE 2 (AE under manager@gmail.com)
    deals = [
        raw_deal(**{
            "Deal ID": "DL-ETHAN-1",
            "Deal Owner": "Ethan Kowalski",
            "Total Contract Value - Year 1 (USD)": 100000.0,
            "Close Date": "2026-07-15T00:00:00",
            "Deal Status": "Closed Won",
        }),
        raw_deal(**{
            "Deal ID": "DL-ETHAN-2",
            "Deal Owner": "Ethan Kowalski",
            "Total Contract Value - Year 1 (USD)": 50000.0,
            "Close Date": "2026-08-10T00:00:00",
            "Deal Status": "Closed Won",
        }),
        raw_deal(**{
            "Deal ID": "DL-SOFIA-1",
            "Deal Owner": "Sofia Brandt",
            "Total Contract Value - Year 1 (USD)": 200000.0,
            "Close Date": "2026-07-20T00:00:00",
            "Deal Status": "Closed Won",
        }),
        raw_deal(**{
            "Deal ID": "DL-OTHER-1",
            "Deal Owner": "Independent Rep",
            "Total Contract Value - Year 1 (USD)": 80000.0,
            "Close Date": "2026-09-01T00:00:00",
            "Deal Status": "Closed Won",
        }),
    ]
    import_deals(database, deals, filename="deals.csv")
    run_calculations(database)
    return database


@pytest.fixture
def client(mock_db):
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def login_token(client, email, password="demo123"):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ── 1. Authentication Tests ──────────────────────────────────────────────────

def test_login_success(client):
    """Successful login returns access token and user metadata."""
    res = client.post(
        "/api/auth/login",
        json={"email": "admin@gmail.com", "password": "demo123"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@gmail.com"
    assert data["user"]["role"] == "Admin"


def test_invalid_login_rejected(client):
    """Wrong password or unknown email returns 401."""
    # Wrong password
    res1 = client.post(
        "/api/auth/login",
        json={"email": "admin@gmail.com", "password": "wrongpassword"},
    )
    assert res1.status_code == 401
    assert "Invalid email or password" in res1.json()["detail"]

    # Unknown email
    res2 = client.post(
        "/api/auth/login",
        json={"email": "ghost@lumberfi.com", "password": "demo123"},
    )
    assert res2.status_code == 401


def test_inactive_user_rejected(client, mock_db):
    """Inactive user cannot log in or access endpoints."""
    # Mark Ethan Kowalski as inactive
    mock_db.users.update_one({"email": "aashrav04@gmail.com"}, {"$set": {"active": False}})

    res = client.post(
        "/api/auth/login",
        json={"email": "aashrav04@gmail.com", "password": "demo123"},
    )
    assert res.status_code == 403
    assert "deactivated" in res.json()["detail"]


def test_auth_me_endpoint(client):
    """GET /api/auth/me returns current authenticated user profile."""
    token = login_token(client, "admin@gmail.com")
    res = client.get("/api/auth/me", headers=auth_header(token))
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "admin@gmail.com"
    assert data["role"] == "Admin"
    assert "hashed_password" not in data


# ── 2. RBAC Data Scoping Tests ───────────────────────────────────────────────

def test_ae_sees_only_own_deals(client):
    """AE Ethan Kowalski can only see his 2 deals."""
    token = login_token(client, "aashrav04@gmail.com")  # Ethan Kowalski
    res = client.get("/api/deals", headers=auth_header(token))
    assert res.status_code == 200
    deals = res.json()["deals"]
    assert len(deals) == 2
    assert all(d["deal_owner"] == "Ethan Kowalski" for d in deals)
    assert res.json()["total"] == 2


def test_ae_cannot_see_another_ae_deals(client):
    """AE Ethan Kowalski cannot see Sofia Brandt's deal even if requested in query."""
    token = login_token(client, "aashrav04@gmail.com")  # Ethan Kowalski
    res = client.get("/api/deals?owner=Sofia+Brandt", headers=auth_header(token))
    assert res.status_code == 200
    deals = res.json()["deals"]
    # Still only sees Ethan Kowalski deals because server locks AE scope
    assert all(d["deal_owner"] == "Ethan Kowalski" for d in deals)


def test_manager_sees_team_data(client):
    """Manager sees deals from their subordinates (Ethan and Sofia), not Independent Rep."""
    token = login_token(client, "manager@gmail.com")
    res = client.get("/api/deals", headers=auth_header(token))
    assert res.status_code == 200
    deals = res.json()["deals"]
    # Team has Ethan Kowalski (2) + Sofia Brandt (1) = 3 deals. Independent Rep is not on team.
    assert len(deals) == 3
    owners = {d["deal_owner"] for d in deals}
    assert owners == {"Ethan Kowalski", "Sofia Brandt"}
    assert "Independent Rep" not in owners


def test_admin_sees_all_deals(client):
    """Admin sees all 4 deals in the database."""
    token = login_token(client, "admin@gmail.com")
    res = client.get("/api/deals", headers=auth_header(token))
    assert res.status_code == 200
    assert res.json()["total"] == 4
    assert len(res.json()["deals"]) == 4


def test_ae_sees_only_own_commissions_and_payouts(client):
    """AE Ethan Kowalski sees only his own commissions and payouts."""
    token = login_token(client, "aashrav04@gmail.com")  # Ethan Kowalski

    # Commissions
    res_comm = client.get("/api/commissions", headers=auth_header(token))
    assert res_comm.status_code == 200
    assert all(c["deal_owner"] == "Ethan Kowalski" for c in res_comm.json()["commissions"])

    # Payouts
    res_pay = client.get("/api/payouts", headers=auth_header(token))
    assert res_pay.status_code == 200
    assert all(p["deal_owner"] == "Ethan Kowalski" for p in res_pay.json()["payouts"])


# ── 3. Administrative Protection Tests ───────────────────────────────────────

def test_ae_cannot_access_admin_upload(client):
    """AE cannot access POST /api/admin/upload."""
    token = login_token(client, "aashrav04@gmail.com")  # Ethan Kowalski
    csv_file = io.BytesIO(b"Deal ID,Deal Name\nD-1,Name")
    res = client.post(
        "/api/admin/upload",
        files={"file": ("deals.csv", csv_file, "text/csv")},
        headers=auth_header(token),
    )
    assert res.status_code == 403
    assert "Admin privilege required" in res.json()["detail"]


def test_ae_cannot_access_admin_calculation(client):
    """AE cannot access POST /api/admin/calculate."""
    token = login_token(client, "aashrav04@gmail.com")  # Ethan Kowalski
    res = client.post("/api/admin/calculate", json={}, headers=auth_header(token))
    assert res.status_code == 403
    assert "Admin privilege required" in res.json()["detail"]


def test_admin_can_access_admin_endpoints(client):
    """Admin can trigger recalculation."""
    token = login_token(client, "admin@gmail.com")
    res = client.post("/api/admin/calculate", json={}, headers=auth_header(token))
    assert res.status_code == 200
    assert res.json()["deals_calculated"] == 4


# ── 4. Dashboard Endpoints Tests ─────────────────────────────────────────────

def test_dashboard_summary_scoped_by_role(client):
    """Dashboard summary metrics are scoped to AE, Manager team, or Company-wide for Admin."""
    # 1. AE: Ethan Kowalski ($100k + $50k = $150k revenue, 2 deals)
    token_ae = login_token(client, "aashrav04@gmail.com")
    res_ae = client.get("/api/dashboard/summary", headers=auth_header(token_ae))
    assert res_ae.status_code == 200
    data_ae = res_ae.json()
    assert data_ae["deal_count"] == 2
    assert data_ae["total_revenue"] == 150000.0
    assert data_ae["target"]["target_amount"] == 300000.0  # 1 AE * 3 mo * $100k
    assert data_ae["target"]["attainment_pct"] == 50.0

    # 2. Manager: Ethan ($150k) + Sofia ($200k) = $350k revenue, 3 deals
    token_mgr = login_token(client, "manager@gmail.com")
    res_mgr = client.get("/api/dashboard/summary", headers=auth_header(token_mgr))
    assert res_mgr.status_code == 200
    data_mgr = res_mgr.json()
    assert data_mgr["deal_count"] == 3
    assert data_mgr["total_revenue"] == 350000.0

    # 3. Admin: All 4 deals ($150k + $200k + $80k = $430k)
    token_admin = login_token(client, "admin@gmail.com")
    res_admin = client.get("/api/dashboard/summary", headers=auth_header(token_admin))
    assert res_admin.status_code == 200
    data_admin = res_admin.json()
    assert data_admin["deal_count"] == 4
    assert data_admin["total_revenue"] == 430000.0


def test_dashboard_performance_endpoint(client):
    """GET /api/dashboard/performance returns AE table sorted by revenue descending."""
    token = login_token(client, "admin@gmail.com")
    res = client.get("/api/dashboard/performance", headers=auth_header(token))
    assert res.status_code == 200
    perf = res.json()
    assert len(perf) == 3  # Sofia ($200k), Ethan ($150k), Independent Rep ($80k)

    # Sorted by revenue descending
    assert perf[0]["owner"] == "Sofia Brandt"
    assert perf[0]["revenue"] == 200000.0
    assert perf[1]["owner"] == "Ethan Kowalski"
    assert perf[1]["revenue"] == 150000.0
    assert perf[2]["owner"] == "Independent Rep"
    assert perf[2]["revenue"] == 80000.0

    assert "MVP assumption" in perf[0]["target_note"]


def test_dashboard_trends_endpoint(client):
    """GET /api/dashboard/trends returns monthly aggregated numbers."""
    token = login_token(client, "admin@gmail.com")
    res = client.get("/api/dashboard/trends", headers=auth_header(token))
    assert res.status_code == 200
    trends = res.json()
    months = [t["month"] for t in trends]
    # Deals closed in July (2026-07), August (2026-08), September (2026-09)
    assert "2026-07" in months
    assert "2026-08" in months
    assert "2026-09" in months
    for t in trends:
        assert "revenue" in t
        assert "commission" in t
        assert "deals" in t


def test_owner_filter_partial_and_case_insensitive(client):
    """
    Regression test for deal owner filtering:
    - Admin searching 'ethan' or 'ETHAN' finds Ethan Kowalski's deals.
    - Manager searching 'ethan' finds Ethan Kowalski's deals (since Ethan is on team).
    - Manager searching an owner not on team returns 0 deals.
    - AE searching another owner still only sees their own deals.
    """
    admin_token = login_token(client, "admin@gmail.com")
    mgr_token = login_token(client, "manager@gmail.com")
    ae_token = login_token(client, "aashrav04@gmail.com")  # Ethan Kowalski

    # 1. Admin searching lowercase 'ethan'
    res_admin_lower = client.get("/api/deals?owner=ethan", headers=auth_header(admin_token))
    assert res_admin_lower.status_code == 200
    deals = res_admin_lower.json()["deals"]
    assert len(deals) == 2
    assert all(d["deal_owner"] == "Ethan Kowalski" for d in deals)

    # 2. Admin searching uppercase 'ETHAN'
    res_admin_upper = client.get("/api/deals?owner=ETHAN", headers=auth_header(admin_token))
    assert res_admin_upper.status_code == 200
    deals_upper = res_admin_upper.json()["deals"]
    assert len(deals_upper) == 2
    assert all(d["deal_owner"] == "Ethan Kowalski" for d in deals_upper)

    # 3. Manager searching 'ethan' (Ethan is on the Manager's team)
    res_mgr_ethan = client.get("/api/deals?owner=ethan", headers=auth_header(mgr_token))
    assert res_mgr_ethan.status_code == 200
    mgr_deals = res_mgr_ethan.json()["deals"]
    assert len(mgr_deals) == 2
    assert all(d["deal_owner"] == "Ethan Kowalski" for d in mgr_deals)

    # 4. Manager searching owner not on team ('Independent') -> 0 deals
    res_mgr_other = client.get("/api/deals?owner=Independent", headers=auth_header(mgr_token))
    assert res_mgr_other.status_code == 200
    assert len(res_mgr_other.json()["deals"]) == 0

    # 5. AE attempting to search another owner ('Sofia' or 'Independent')
    res_ae_tamper = client.get("/api/deals?owner=Sofia", headers=auth_header(ae_token))
    assert res_ae_tamper.status_code == 200
    ae_deals = res_ae_tamper.json()["deals"]
    assert len(ae_deals) == 2
    assert all(d["deal_owner"] == "Ethan Kowalski" for d in ae_deals)

