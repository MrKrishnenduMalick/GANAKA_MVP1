"""Milestone 4 integration tests — Financial Reconciliation Engine.

Runs against the live preview deployment (same surface as Milestone 1/2/3 tests).
Reconciliation runs against seeded Shopify orders and Razorpay payments/refunds/settlements.
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


def seed_shopify_order(workspace_id: str, shopify_id: int, total: float = 100.00, gateway: str = "Razorpay") -> str:
    now = datetime.now(timezone.utc)
    order_id = str(uuid.uuid4())
    db.shopify_order.insert_one(
        {
            "_id": order_id,
            "workspace_id": workspace_id,
            "shopify_id": shopify_id,
            "order_number": shopify_id,
            "customer_id": None,
            "currency": "INR",
            "subtotal": total,
            "tax": 0.0,
            "shipping": 0.0,
            "discount": 0.0,
            "total": total,
            "status": "paid",
            "financial_status": "paid",
            "fulfillment_status": None,
            "payment_gateway_names": [gateway],
            "presentment_currency": "INR",
            "gift_card_amount_used": 0.0,
            "shopify_created_at": now,
            "shopify_updated_at": now,
            "raw": {},
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
    )
    return order_id


def seed_razorpay_payment(workspace_id: str, razorpay_id: str, order_id: str, amount: float = 100.0, status: str = "captured") -> str:
    now = datetime.now(timezone.utc)
    payment_id = str(uuid.uuid4())
    db.razorpay_payment.insert_one(
        {
            "_id": payment_id,
            "workspace_id": workspace_id,
            "razorpay_id": razorpay_id,
            "order_id": order_id,
            "amount": amount,
            "currency": "INR",
            "status": status,
            "method": "card",
            "fee": 0.0,
            "tax": 0.0,
            "captured": status == "captured",
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


class TestReconciliationEngine:
    @pytest.fixture(scope="class")
    def owner(self):
        email = seed_verified_user("reconowner", "Reconciliation Alpha")
        response = login(email)
        assert response.status_code == 200, response.text
        return {"email": email, **response.json()}

    def test_run_requires_authentication(self):
        response = requests.post(f"{API}/reconciliation/run", timeout=30)
        assert response.status_code == 401
        assert response.json()["code"] == "AUTH-003"

    def test_run_requires_reconciliation_run_permission(self, owner):
        viewer_email = seed_verified_user("reconviewer", "Reconciliation Viewer Home")
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
            f"{API}/reconciliation/run",
            headers=auth_headers(viewer_token),
            timeout=30,
        )
        assert response.status_code == 403
        assert response.json()["code"] == "AUTHZ-001"

    def test_run_creates_job_and_results(self, owner):
        workspace_id = owner["workspace"]["id"]
        seed_shopify_order(workspace_id, 1001, total=100.0)
        seed_razorpay_payment(workspace_id, "pay_1001", "order_1001", amount=100.0)

        headers = auth_headers(owner["access_token"])
        response = requests.post(f"{API}/reconciliation/run", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert "job_id" in body
        assert body["status"] == "COMPLETED"

        results = requests.get(f"{API}/reconciliation/results", headers=headers, timeout=30)
        assert results.status_code == 200
        results_body = results.json()
        assert results_body["total"] >= 1

    def test_summary_returns_counts(self, owner):
        headers = auth_headers(owner["access_token"])
        response = requests.get(f"{API}/reconciliation/summary", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert "total_orders" in body
        assert "matched" in body
        assert "match_rate" in body

    def test_exceptions_list_empty_when_none(self, owner):
        headers = auth_headers(owner["access_token"])
        response = requests.get(f"{API}/reconciliation/exceptions", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert "items" in body

    def test_idempotent_run_returns_existing_job(self, owner):
        headers = auth_headers(owner["access_token"])
        first = requests.post(f"{API}/reconciliation/run", headers=headers, timeout=30)
        assert first.status_code == 200
        second = requests.post(f"{API}/reconciliation/run", headers=headers, timeout=30)
        assert second.status_code == 200
        assert second.json()["job_id"] == first.json()["job_id"]

    def test_reconciliation_indexes_exist(self):
        assert "ux_recon_job_idempotency" in db.reconciliation_job.index_information()
        assert "ix_recon_result_workspace_created" in db.reconciliation_result.index_information()
        assert "ix_recon_exception_workspace_created" in db.reconciliation_exception.index_information()