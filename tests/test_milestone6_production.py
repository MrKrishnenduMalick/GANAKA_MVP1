"""Milestone 6 integration tests — Production Readiness.

Runs against the live preview deployment (same surface as previous milestones).
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


class TestProductionReadiness:
    @pytest.fixture(scope="class")
    def owner(self):
        email = seed_verified_user("prodowner", "Production Alpha")
        response = login(email)
        assert response.status_code == 200, response.text
        return {"email": email, **response.json()}

    def test_health_endpoints_public(self):
        response = requests.get(f"{API}/health", timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert "status" in body
        assert "database" in body
        assert "integrations" in body

    def test_health_database_endpoint(self):
        response = requests.get(f"{API}/health/database", timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert "status" in body
        assert "latency_ms" in body
        assert "collections" in body

    def test_health_integration_endpoints(self, owner):
        headers = auth_headers(owner["access_token"])
        for integration in ["shopify", "razorpay", "reconciliation"]:
            response = requests.get(f"{API}/health/{integration}", headers=headers, timeout=30)
            assert response.status_code == 200
            body = response.json()
            assert "status" in body
            assert "configured" in body

    def test_export_requires_report_export_permission(self, owner):
        viewer_email = seed_verified_user("prodviewer", "Production Viewer Home")
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

        export_request = {
            "format": "csv",
            "date_from": "2020-01-01T00:00:00Z",
            "date_to": "2030-01-01T00:00:00Z",
        }
        response = requests.post(
            f"{API}/exports/reconciliation-results",
            json=export_request,
            headers=auth_headers(viewer_token),
            timeout=30,
        )
        assert response.status_code == 403
        assert response.json()["code"] == "AUTHZ-001"

    def test_export_reconciliation_results(self, owner):
        headers = auth_headers(owner["access_token"])
        export_request = {
            "format": "csv",
            "date_from": "2020-01-01T00:00:00Z",
            "date_to": "2030-01-01T00:00:00Z",
        }
        response = requests.post(
            f"{API}/exports/reconciliation-results",
            json=export_request,
            headers=headers,
            timeout=30,
        )
        assert response.status_code == 200
        body = response.json()
        assert "download_url" in body
        assert "filename" in body
        assert "format" in body
        assert "record_count" in body
        assert body["format"] == "csv"

    def test_export_exceptions(self, owner):
        headers = auth_headers(owner["access_token"])
        export_request = {
            "format": "excel",
            "date_from": "2020-01-01T00:00:00Z",
            "date_to": "2030-01-01T00:00:00Z",
        }
        response = requests.post(
            f"{API}/exports/exceptions",
            json=export_request,
            headers=headers,
            timeout=30,
        )
        assert response.status_code == 200
        body = response.json()
        assert "download_url" in body
        assert body["format"] == "excel"

    def test_export_dashboard_summary(self, owner):
        headers = auth_headers(owner["access_token"])
        export_request = {
            "format": "pdf",
            "date_from": "2020-01-01T00:00:00Z",
            "date_to": "2030-01-01T00:00:00Z",
        }
        response = requests.post(
            f"{API}/exports/dashboard-summary",
            json=export_request,
            headers=headers,
            timeout=30,
        )
        assert response.status_code == 200
        body = response.json()
        assert "download_url" in body
        assert body["format"] == "pdf"

    def test_export_payments(self, owner):
        headers = auth_headers(owner["access_token"])
        export_request = {
            "format": "csv",
            "date_from": "2020-01-01T00:00:00Z",
            "date_to": "2030-01-01T00:00:00Z",
        }
        response = requests.post(
            f"{API}/exports/payments",
            json=export_request,
            headers=headers,
            timeout=30,
        )
        assert response.status_code == 200
        body = response.json()
        assert "download_url" in body
        assert body["format"] == "csv"

    def test_export_refunds(self, owner):
        headers = auth_headers(owner["access_token"])
        export_request = {
            "format": "csv",
            "date_from": "2020-01-01T00:00:00Z",
            "date_to": "2030-01-01T00:00:00Z",
        }
        response = requests.post(
            f"{API}/exports/refunds",
            json=export_request,
            headers=headers,
            timeout=30,
        )
        assert response.status_code == 200
        body = response.json()
        assert "download_url" in body
        assert body["format"] == "csv"

    def test_export_settlements(self, owner):
        headers = auth_headers(owner["access_token"])
        export_request = {
            "format": "csv",
            "date_from": "2020-01-01T00:00:00Z",
            "date_to": "2030-01-01T00:00:00Z",
        }
        response = requests.post(
            f"{API}/exports/settlements",
            json=export_request,
            headers=headers,
            timeout=30,
        )
        assert response.status_code == 200
        body = response.json()
        assert "download_url" in body
        assert body["format"] == "csv"

    def test_notification_preferences(self, owner):
        headers = auth_headers(owner["access_token"])
        response = requests.get(f"{API}/notifications/preferences", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert "critical_reconciliation_failures" in body
        assert "failed_shopify_sync" in body
        assert "failed_razorpay_sync" in body
        assert "oauth_expiration" in body
        assert "webhook_failures" in body

    def test_update_notification_preferences(self, owner):
        headers = auth_headers(owner["access_token"])
        update_data = {
            "email_enabled": True,
            "webhook_url": "https://example.com/webhook",
        }
        response = requests.patch(
            f"{API}/notifications/preferences",
            json=update_data,
            headers=headers,
            timeout=30,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["email_enabled"] is True
        assert body["webhook_url"] == "https://example.com/webhook"