"""Milestone 2 / Feature 2.2 integration tests — Shopify Initial Data Sync.

Runs against the live preview deployment (same surface as Milestone 1 tests).
Shopify Partner credentials are not configured, so the live HTTP round-trip
cannot be exercised; those paths are covered by the unconfigured -> EXTERNAL-001
assertions and by the seeded-data tests for list/filter/pagination.
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


def seed_shopify_connection(workspace_id: str, shop_domain: str) -> str:
    now = datetime.now(timezone.utc)
    connection_id = str(uuid.uuid4())
    db.shopify_connection.insert_one(
        {
            "_id": connection_id,
            "workspace_id": workspace_id,
            "shop_domain": shop_domain,
            "shop_name": "QA Store",
            "access_token_encrypted": "fixture-encrypted-token",
            "scopes": "read_orders,read_products,read_customers",
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


def seed_shopify_order(workspace_id: str, shopify_id: int) -> str:
    now = datetime.now(timezone.utc)
    order_id = str(uuid.uuid4())
    db.shopify_order.insert_one(
        {
            "_id": order_id,
            "workspace_id": workspace_id,
            "shopify_id": shopify_id,
            "order_number": 1001,
            "customer_id": 5001,
            "currency": "INR",
            "subtotal": 1000.0,
            "tax": 180.0,
            "shipping": 50.0,
            "discount": 0.0,
            "total": 1230.0,
            "status": "paid",
            "financial_status": "paid",
            "fulfillment_status": None,
            "payment_gateway_names": ["razorpay"],
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


def seed_shopify_product(workspace_id: str, shopify_id: int) -> str:
    now = datetime.now(timezone.utc)
    product_id = str(uuid.uuid4())
    db.shopify_product.insert_one(
        {
            "_id": product_id,
            "workspace_id": workspace_id,
            "shopify_id": shopify_id,
            "title": "QA T-Shirt",
            "handle": "qa-t-shirt",
            "product_type": "Apparel",
            "vendor": "QA Vendor",
            "status": "active",
            "shopify_created_at": now,
            "shopify_updated_at": now,
            "raw": {},
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
    )
    return product_id


def seed_shopify_customer(workspace_id: str, shopify_id: int) -> str:
    now = datetime.now(timezone.utc)
    customer_id = str(uuid.uuid4())
    db.shopify_customer.insert_one(
        {
            "_id": customer_id,
            "workspace_id": workspace_id,
            "shopify_id": shopify_id,
            "email": "qa-customer@example.com",
            "first_name": "QA",
            "last_name": "Customer",
            "phone": "+919999999999",
            "tags": ["vip"],
            "shopify_created_at": now,
            "shopify_updated_at": now,
            "raw": {},
            "created_at": now,
            "updated_at": now,
            "deleted_at": None,
        }
    )
    return customer_id


def auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


class TestShopifySync:
    @pytest.fixture(scope="class")
    def owner(self):
        email = seed_verified_user("syncowner", "Sync Alpha")
        response = login(email)
        assert response.status_code == 200, response.text
        return {"email": email, **response.json()}

    def test_sync_requires_authentication(self):
        response = requests.post(f"{API}/shopify/sync", json={"resources": ["orders"]}, timeout=30)
        assert response.status_code == 401
        assert response.json()["code"] == "AUTH-003"

    def test_sync_requires_connect_permission(self, owner):
        viewer_email = seed_verified_user("syncviewer", "Sync Viewer Home")
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
            f"{API}/shopify/sync",
            json={"resources": ["orders"]},
            headers=auth_headers(viewer_token),
            timeout=30,
        )
        assert response.status_code == 403
        assert response.json()["code"] == "AUTHZ-001"

    def test_sync_returns_external_001_when_unconfigured(self, owner):
        response = requests.post(
            f"{API}/shopify/sync",
            json={"resources": ["orders"]},
            headers=auth_headers(owner["access_token"]),
            timeout=30,
        )
        assert response.status_code == 503
        assert response.json()["code"] == "EXTERNAL-001"

    def test_sync_status_returns_404_for_unknown_job(self, owner):
        response = requests.get(
            f"{API}/shopify/sync/status/{uuid.uuid4()}", headers=auth_headers(owner["access_token"]), timeout=30
        )
        assert response.status_code == 404
        assert response.json()["code"] == "SHOPIFY-006"

    def test_orders_list_empty_when_no_data(self, owner):
        response = requests.get(f"{API}/shopify/orders", headers=auth_headers(owner["access_token"]), timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["page"] == 1

    def test_orders_list_pagination_and_filter(self, owner):
        workspace_id = owner["workspace"]["id"]
        seed_shopify_order(workspace_id, 1001)
        seed_shopify_order(workspace_id, 1002)
        seed_shopify_order(workspace_id, 1003)
        headers = auth_headers(owner["access_token"])

        response = requests.get(f"{API}/shopify/orders?page=1&page_size=2", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 2
        assert body["total"] == 3
        assert body["total_pages"] == 2

        filtered = requests.get(
            f"{API}/shopify/orders?financial_status=paid", headers=headers, timeout=30
        )
        assert filtered.status_code == 200
        assert filtered.json()["total"] == 3

    def test_products_list(self, owner):
        workspace_id = owner["workspace"]["id"]
        seed_shopify_product(workspace_id, 2001)
        headers = auth_headers(owner["access_token"])

        response = requests.get(f"{API}/shopify/products?page=1&page_size=10", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["title"] == "QA T-Shirt"

    def test_customers_list(self, owner):
        workspace_id = owner["workspace"]["id"]
        seed_shopify_customer(workspace_id, 3001)
        headers = auth_headers(owner["access_token"])

        response = requests.get(f"{API}/shopify/customers?page=1&page_size=10", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["email"] == "qa-customer@example.com"

    def test_idempotent_import_no_duplicates(self, owner):
        """Seeding the same shopify_id twice must not create duplicates (unique index)."""
        workspace_id = owner["workspace"]["id"]
        seed_shopify_order(workspace_id, 5001)
        seed_shopify_order(workspace_id, 5001)
        count = db.shopify_order.count_documents({"workspace_id": workspace_id, "shopify_id": 5001})
        assert count == 1

    def test_sync_job_indexes_exist(self):
        assert "ix_shopify_sync_job_workspace_created" in db.shopify_sync_job.index_information()
        for coll in ("shopify_order", "shopify_product", "shopify_customer"):
            info = db[coll].index_information()
            assert f"ux_{coll}_workspace_shopify" in info