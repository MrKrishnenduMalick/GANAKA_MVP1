"""Milestone 3 integration tests — Razorpay Integration.

Runs against the live preview deployment (same surface as Milestone 1/2 tests).
Razorpay credentials are not configured, so the live API round-trip cannot be
exercised; those paths are covered by the unconfigured -> EXTERNAL-001
assertions and by the seeded-data tests for list/filter/pagination.
"""

import hashlib
import hmac
import json
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


def seed_razorpay_connection(workspace_id: str, key_id: str) -> str:
    now = datetime.now(timezone.utc)
    connection_id = str(uuid.uuid4())
    db.razorpay_connection.insert_one(
        {
            "_id": connection_id,
            "workspace_id": workspace_id,
            "key_id": key_id,
            "key_secret_encrypted": "fixture-encrypted-secret",
            "account_name": "QA Account",
            "account_email": "qa@razorpay.com",
            "installed_at": now,
            "status": "ACTIVE",
            "disconnected_at": None,
            "last_verified_at": now,
            "metadata": {},
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
    )
    return connection_id


def seed_razorpay_payment(workspace_id: str, razorpay_id: str) -> str:
    now = datetime.now(timezone.utc)
    payment_id = str(uuid.uuid4())
    db.razorpay_payment.insert_one(
        {
            "_id": payment_id,
            "workspace_id": workspace_id,
            "razorpay_id": razorpay_id,
            "order_id": "order_123",
            "amount": 1000.0,
            "currency": "INR",
            "status": "captured",
            "method": "card",
            "fee": 10.0,
            "tax": 1.8,
            "captured": True,
            "refunded": False,
            "razorpay_created_at": now,
            "razorpay_updated_at": now,
            "raw": {},
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
    )
    return payment_id


def auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


class TestRazorpayIntegration:
    @pytest.fixture(scope="class")
    def owner(self):
        email = seed_verified_user("razorowner", "Razorpay Alpha")
        response = login(email)
        assert response.status_code == 200, response.text
        return {"email": email, **response.json()}

    def test_connect_requires_authentication(self):
        response = requests.post(f"{API}/razorpay/connect", timeout=30)
        assert response.status_code == 401
        assert response.json()["code"] == "AUTH-003"

    def test_connect_requires_razorpay_connect_permission(self, owner):
        viewer_email = seed_verified_user("razorviewer", "Razorpay Viewer Home")
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

        response = requests.post(
            f"{API}/razorpay/connect",
            headers=auth_headers(viewer_token),
            timeout=30,
        )
        assert response.status_code == 403
        assert response.json()["code"] == "AUTHZ-001"

    def test_connect_returns_external_001_when_unconfigured(self, owner):
        response = requests.post(
            f"{API}/razorpay/connect",
            headers=auth_headers(owner["access_token"]),
            timeout=30,
        )
        assert response.status_code == 503
        assert response.json()["code"] == "EXTERNAL-001"

    def test_status_returns_false_when_not_connected(self, owner):
        response = requests.get(
            f"{API}/razorpay/status",
            headers=auth_headers(owner["access_token"]),
            timeout=30,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["connected"] is False
        assert body["connection"] is None

    def test_payments_list_empty_when_no_data(self, owner):
        response = requests.get(
            f"{API}/razorpay/payments",
            headers=auth_headers(owner["access_token"]),
            timeout=30,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_payments_list_pagination_and_filter(self, owner):
        workspace_id = owner["workspace"]["id"]
        seed_razorpay_payment(workspace_id, "pay_001")
        seed_razorpay_payment(workspace_id, "pay_002")
        headers = auth_headers(owner["access_token"])

        response = requests.get(f"{API}/razorpay/payments?page=1&page_size=1", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 1
        assert body["total"] == 2
        assert body["total_pages"] == 2

        filtered = requests.get(
            f"{API}/razorpay/payments?status=captured", headers=headers, timeout=30
        )
        assert filtered.status_code == 200
        assert filtered.json()["total"] == 2

    def test_refunds_list(self, owner):
        workspace_id = owner["workspace"]["id"]
        seed_razorpay_payment(workspace_id, "pay_003")
        headers = auth_headers(owner["access_token"])

        response = requests.get(f"{API}/razorpay/refunds?page=1&page_size=10", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0

    def test_settlements_list(self, owner):
        headers = auth_headers(owner["access_token"])
        response = requests.get(f"{API}/razorpay/settlements?page=1&page_size=10", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0

    def test_idempotent_import_no_duplicates(self, owner):
        workspace_id = owner["workspace"]["id"]
        seed_razorpay_payment(workspace_id, "pay_dup")
        seed_razorpay_payment(workspace_id, "pay_dup")
        count = db.razorpay_payment.count_documents({"workspace_id": workspace_id, "razorpay_id": "pay_dup"})
        assert count == 1

    def test_razorpay_indexes_exist(self):
        assert "ux_razorpay_connection_workspace" in db.razorpay_connection.index_information()
        for coll in ("razorpay_payment", "razorpay_refund", "razorpay_settlement"):
            info = db[coll].index_information()
            assert f"ux_{coll}_workspace_razorpay" in info