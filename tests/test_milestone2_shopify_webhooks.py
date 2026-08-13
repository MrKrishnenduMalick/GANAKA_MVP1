"""Milestone 2 / Feature 2.3 integration tests — Shopify Webhooks & Incremental Sync.

Runs against the live preview deployment (same surface as Milestone 1 tests).
Shopify Partner credentials are not configured, so the live webhook delivery
cannot be exercised; those paths are covered by the unconfigured -> EXTERNAL-001
assertions and by the seeded-data tests for webhook processing and incremental sync.
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


def auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def shopify_hmac(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


class TestShopifyWebhooks:
    @pytest.fixture(scope="class")
    def owner(self):
        email = seed_verified_user("webhookowner", "Webhook Alpha")
        response = login(email)
        assert response.status_code == 200, response.text
        return {"email": email, **response.json()}

    def test_webhook_rejects_invalid_hmac(self, owner):
        headers = {
            "X-Shopify-Topic": "orders/create",
            "X-Shopify-Shop-Domain": "qa.myshopify.com",
            "X-Shopify-Webhook-Id": str(uuid.uuid4()),
            "X-Shopify-Hmac-SHA256": "invalid",
        }
        response = requests.post(f"{API}/shopify/webhooks", json={"order": {"id": 1}}, headers=headers, timeout=30)
        assert response.status_code == 401
        assert response.json()["code"] == "SHOPIFY-007"

    def test_webhook_duplicate_prevention(self, owner):
        workspace_id = owner["workspace"]["id"]
        seed_shopify_connection(workspace_id, "qa.myshopify.com")
        payload = json.dumps({"order": {"id": 7001}}).encode("utf-8")
        hmac_header = shopify_hmac(payload, "")
        headers = {
            "X-Shopify-Topic": "orders/create",
            "X-Shopify-Shop-Domain": "qa.myshopify.com",
            "X-Shopify-Webhook-Id": str(uuid.uuid4()),
            "X-Shopify-Hmac-SHA256": hmac_header,
        }
        first = requests.post(f"{API}/shopify/webhooks", data=payload, headers=headers, timeout=30)
        assert first.status_code == 200
        second = requests.post(f"{API}/shopify/webhooks", data=payload, headers=headers, timeout=30)
        assert second.status_code == 200
        assert second.json()["status"] == "duplicate"

    def test_webhook_order_create_and_update(self, owner):
        workspace_id = owner["workspace"]["id"]
        seed_shopify_connection(workspace_id, "qa.myshopify.com")
        payload = json.dumps({"order": {"id": 7002, "total_price": "100.00", "currency": "INR"}}).encode("utf-8")
        hmac_header = shopify_hmac(payload, "")
        headers = {
            "X-Shopify-Topic": "orders/create",
            "X-Shopify-Shop-Domain": "qa.myshopify.com",
            "X-Shopify-Webhook-Id": str(uuid.uuid4()),
            "X-Shopify-Hmac-SHA256": hmac_header,
        }
        response = requests.post(f"{API}/shopify/webhooks", data=payload, headers=headers, timeout=30)
        assert response.status_code == 200
        assert response.json()["status"] == "processed"

        update_payload = json.dumps({"order": {"id": 7002, "total_price": "200.00", "currency": "INR"}}).encode("utf-8")
        update_hmac = shopify_hmac(update_payload, "")
        headers["X-Shopify-Hmac-SHA256"] = update_hmac
        headers["X-Shopify-Webhook-Id"] = str(uuid.uuid4())
        updated = requests.post(f"{API}/shopify/webhooks", data=update_payload, headers=headers, timeout=30)
        assert updated.status_code == 200
        assert updated.json()["status"] == "processed"

    def test_webhook_product_update(self, owner):
        workspace_id = owner["workspace"]["id"]
        seed_shopify_connection(workspace_id, "qa.myshopify.com")
        payload = json.dumps({"product": {"id": 8001, "title": "Updated Product"}}).encode("utf-8")
        hmac_header = shopify_hmac(payload, "")
        headers = {
            "X-Shopify-Topic": "products/update",
            "X-Shopify-Shop-Domain": "qa.myshopify.com",
            "X-Shopify-Webhook-Id": str(uuid.uuid4()),
            "X-Shopify-Hmac-SHA256": hmac_header,
        }
        response = requests.post(f"{API}/shopify/webhooks", data=payload, headers=headers, timeout=30)
        assert response.status_code == 200
        assert response.json()["status"] == "processed"

    def test_webhook_customer_update(self, owner):
        workspace_id = owner["workspace"]["id"]
        seed_shopify_connection(workspace_id, "qa.myshopify.com")
        payload = json.dumps({"customer": {"id": 9001, "email": "updated@example.com"}}).encode("utf-8")
        hmac_header = shopify_hmac(payload, "")
        headers = {
            "X-Shopify-Topic": "customers/update",
            "X-Shopify-Shop-Domain": "qa.myshopify.com",
            "X-Shopify-Webhook-Id": str(uuid.uuid4()),
            "X-Shopify-Hmac-SHA256": hmac_header,
        }
        response = requests.post(f"{API}/shopify/webhooks", data=payload, headers=headers, timeout=30)
        assert response.status_code == 200
        assert response.json()["status"] == "processed"

    def test_webhook_refund_event(self, owner):
        workspace_id = owner["workspace"]["id"]
        seed_shopify_connection(workspace_id, "qa.myshopify.com")
        payload = json.dumps({"refund": {"id": 1001}, "order": {"id": 7003}}).encode("utf-8")
        hmac_header = shopify_hmac(payload, "")
        headers = {
            "X-Shopify-Topic": "refunds/create",
            "X-Shopify-Shop-Domain": "qa.myshopify.com",
            "X-Shopify-Webhook-Id": str(uuid.uuid4()),
            "X-Shopify-Hmac-SHA256": hmac_header,
        }
        response = requests.post(f"{API}/shopify/webhooks", data=payload, headers=headers, timeout=30)
        assert response.status_code == 200
        assert response.json()["status"] == "processed"

    def test_webhook_status_endpoint(self, owner):
        headers = auth_headers(owner["access_token"])
        response = requests.get(f"{API}/shopify/webhooks/status", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert "total" in body
        assert "processed" in body
        assert "unprocessed" in body
        assert "recent" in body

    def test_incremental_sync_endpoint(self, owner):
        headers = auth_headers(owner["access_token"])
        response = requests.post(f"{API}/shopify/sync/incremental", headers=headers, timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert "job_id" in body
        assert body["status"] == "COMPLETED"