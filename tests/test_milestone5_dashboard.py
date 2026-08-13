"""Milestone 5 integration tests — Dashboard & Analytics API.

Runs against the live preview deployment (same surface as Milestone 1/2/3/4 tests).
"""

import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
FRONTEND_ENV = Path(__file__).resolve().parents[1] / "frontend" / ".env"
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(FRONTEND_ENV)
sys.path.insert(0, str(BACKEND_DIR))

from app.core.db import SYSTEM_ROLE_PERMISSIONS  # noqa: E402
from app.core.security import hash_password  # noqa: E402

API = f"{os.environ['REACT_APP_BACKEND_URL']}/api/v1"
mongo = MongoClient(os.environ["MONGO_URL"])
db = mongo[os.environ["DB_NAME"]]

PASSWORD = "Ganaka#Test2026x"


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@ganakaqa.dev"


def login(email: str, password: str = PASSWORD) -> requests.Response:
    response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    if response.status_code == 429:
        time.sleep(61)
        response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    return response


def seed_verified_user(prefix: str, workspace_name: str) -> str:
    email = unique_email(prefix)
    now = datetime.now(timezone.utc)
    user_id = str(uuid.uuid4())
    workspace_id = str(uuid.uuid4())
    slug = f"{prefix}-{uuid.uuid4().hex[:8]}"

    db.user.insert_one(
        {
            "_id": user_id,
            "email": email,
            "full_name": "QA Person",
            "phone": None,
            "profile_image_url": None,
            "password_hash": hash_password(PASSWORD),
            "status": "ACTIVE",
            "email_verified_at": now,
            "failed_login_count": 0,
            "locked_until": None,
            "last_login_at": None,
            "default_workspace_id": workspace_id,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
    )
    db.workspace.insert_one(
        {
            "_id": workspace_id,
            "name": workspace_name,
            "slug": slug,
            "status": "ACTIVE",
            "owner_id": user_id,
            "plan": "FREE",
            "timezone": "Asia/Kolkata",
            "currency": "INR",
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
    )
    for role_name, permissions in SYSTEM_ROLE_PERMISSIONS.items():
        db.role.insert_one(
            {
                "_id": str(uuid.uuid4()),
                "workspace_id": workspace_id,
                "name": role_name,
                "description": f"Default {role_name.title()} role",
                "permissions": permissions,
                "is_system": True,
                "created_at": now,
                "updated_at": now,
                "deleted_at": None,
            }
        )
    db.workspace_member.insert_one(
        {
            "_id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "user_id": user_id,
            "email": email,
            "full_name": "QA Person",
            "roles": ["OWNER"],
            "status": "ACTIVE",
            "invited_by": None,
            "joined_at": now,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
    )
    db.workspace_settings.insert_one(
        {
            "_id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "company_name": workspace_name,
            "timezone": "Asia/Kolkata",
            "currency": "INR",
            "logo_url": None,
            "theme": "SYSTEM",
            "language": "en",
            "notification_settings": {"email_enabled": True},
            "security_settings": {"enforce_session_limit": True},
            "reconciliation_amount_tolerance": 0.00,
            "settlement_match_window_days": 15,
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
    )
    return email


def auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


class TestDashboardAnalytics:
    @pytest.fixture(scope="class")
    def owner(self):
        email = seed_verified_user("dashowner", "Dashboard Alpha")
        response = login(email)
        assert response.status_code == 200, response.text
        return {"email": email, **response.json()}

    def test_overview_requires_authentication(self):
        response = requests.get(f"{API}/dashboard/overview", timeout=30)
        assert response.status_code == 401
        assert response.json()["code"] == "AUTH-003"

    def test_overview_requires_dashboard_read_permission(self, owner):
        viewer_email = seed_verified_user("dashviewer", "Dashboard Viewer Home")
        headers = auth_headers(owner["access_token"])
        invitation = requests.post(
            f"{API}/workspaces/invitations",
            json={"email": viewer_email, "role": "VIEWER"},
            headers=headers,
            timeout=30,
        )
        assert invitation.status_code == 201
        body = db.outbound_email.find_one(
            {"to_email": viewer_email, "template": "WORKSPACE_INVITATION"}, sort=[("created_at", -1)]
        )
        assert body
        marker = "token="
        start = body["body"].index(marker) + len(marker)
        invite_token = body["body"][start:].split()[0].strip()

        viewer_login = login(viewer_email)
        assert viewer_login.status_code == 200, viewer_login.text
        viewer_headers = auth_headers(viewer_login.json()["access_token"])
        accepted = requests.post(
            f"{API}/workspaces/invitations/accept", json={"token": invite_token}, headers=viewer_headers, timeout=30
        )
        assert accepted.status_code == 200
        switched = requests.post(
            f"{API}/workspaces/{owner['workspace']['id']}/switch", headers=viewer_headers, timeout=30
        )
        assert switched.status_code == 200
        viewer_token = switched.json()["access_token"]

        response = requests.get(
            f"{API}/dashboard/overview", headers=auth_headers(viewer_token), timeout=30
        )
        assert response.status_code == 403
        assert response.json()["code"] == "AUTHZ-001"

    def test_overview_returns_cards(self, owner):
        headers = auth_headers(owner["access_token"])
        response = requests.get(f"{API}/dashboard/overview", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert "revenue" in body
        assert "total_orders" in body
        assert "total_payments" in body
        assert "total_refunds" in body
        assert "total_settlements" in body
        assert "reconciliation_match_rate" in body
        assert "total_exceptions" in body
        assert "critical_exceptions" in body
        assert "pending_exceptions" in body
        assert "connected_integrations" in body

    def test_revenue_returns_trends(self, owner):
        headers = auth_headers(owner["access_token"])
        response = requests.get(f"{API}/dashboard/revenue", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert "total" in body
        assert "daily" in body
        assert "weekly" in body
        assert "monthly" in body

    def test_orders_returns_trend(self, owner):
        headers = auth_headers(owner["access_token"])
        response = requests.get(f"{API}/dashboard/orders", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert "total" in body
        assert "trend" in body

    def test_payments_returns_trend(self, owner):
        headers = auth_headers(owner["access_token"])
        response = requests.get(f"{API}/dashboard/payments", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert "total" in body
        assert "trend" in body

    def test_refunds_returns_trend(self, owner):
        headers = auth_headers(owner["access_token"])
        response = requests.get(f"{API}/dashboard/refunds", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert "total" in body
        assert "trend" in body

    def test_settlements_returns_trend(self, owner):
        headers = auth_headers(owner["access_token"])
        response = requests.get(f"{API}/dashboard/settlements", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert "total" in body
        assert "trend" in body

    def test_exceptions_returns_trend(self, owner):
        headers = auth_headers(owner["access_token"])
        response = requests.get(f"{API}/dashboard/exceptions", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert "total" in body
        assert "critical" in body
        assert "pending" in body
        assert "trend" in body

    def test_match_rate_returns_trend(self, owner):
        headers = auth_headers(owner["access_token"])
        response = requests.get(f"{API}/dashboard/match-rate", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert "rate" in body
        assert "trend" in body

    def test_analytics_returns_full_payload(self, owner):
        headers = auth_headers(owner["access_token"])
        response = requests.get(f"{API}/dashboard/analytics", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert "revenue" in body
        assert "orders" in body
        assert "payments" in body
        assert "refunds" in body
        assert "settlements" in body
        assert "exceptions" in body
        assert "match_rate" in body

    def test_dashboard_filters_by_date_range(self, owner):
        headers = auth_headers(owner["access_token"])
        response = requests.get(
            f"{API}/dashboard/overview?date_from=2020-01-01T00:00:00Z&date_to=2030-01-01T00:00:00Z",
            headers=headers,
            timeout=30,
        )
        assert response.status_code == 200
        body = response.json()
        assert "revenue" in body