"""Milestone 2 / Feature 2.1 integration tests — Shopify OAuth.

Runs against the live preview deployment (the same surface the frontend uses),
following the Milestone 1 test conventions. Shopify Partner credentials are not
configured in this environment, so the live OAuth round-trip (install URL ->
Shopify authorize -> callback -> token exchange -> store verification) cannot
be exercised; those paths are covered by the unconfigured -> EXTERNAL-001
assertions and by the seeded-connection tests for status/disconnect/audit.
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

from app.core.db import SYSTEM_ROLE_PERMISSIONS  # noqa: E402  (needs the .env loaded first)
from app.core.security import hash_password  # noqa: E402

API = f"{os.environ['REACT_APP_BACKEND_URL']}/api/v1"
mongo = MongoClient(os.environ["MONGO_URL"])
db = mongo[os.environ["DB_NAME"]]

PASSWORD = "Ganaka#Test2026x"


def unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}@ganakaqa.dev"


def login(email: str, password: str = PASSWORD) -> requests.Response:
    """Login, tolerating the per-IP rate limit that protects this endpoint."""
    response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    if response.status_code == 429:
        time.sleep(61)
        response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    return response


def seed_verified_user(prefix: str, workspace_name: str) -> str:
    """Create an ACTIVE user + owned workspace directly in MongoDB.

    Registration is rate limited to 5/hour per IP by design, so fixtures seed
    accounts instead of burning that budget. Role permissions come from the
    application's own SYSTEM_ROLE_PERMISSIONS map so the fixture cannot drift.
    """
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
    db.audit_log.insert_one(
        {
            "_id": str(uuid.uuid4()),
            "action": "WORKSPACE_CREATED",
            "status": "SUCCESS",
            "actor_user_id": user_id,
            "workspace_id": workspace_id,
            "resource_type": "WORKSPACE",
            "resource_id": workspace_id,
            "ip": None,
            "user_agent": "pytest-fixture",
            "request_id": None,
            "metadata": {"name": workspace_name},
            "created_at": now,
            "updated_at": now,
        }
    )
    return email


def seed_shopify_connection(workspace_id: str, shop_domain: str) -> str:
    """Insert an ACTIVE Shopify connection directly (encrypted token is a fixture)."""
    now = datetime.now(timezone.utc)
    connection_id = str(uuid.uuid4())
    db.shopify_connection.insert_one(
        {
            "_id": connection_id,
            "workspace_id": workspace_id,
            "shop_domain": shop_domain,
            "shop_name": "QA Store",
            "access_token_encrypted": "fixture-encrypted-token",
            "scopes": "read_orders,read_products",
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


class TestShopifyOAuth:
    @pytest.fixture(scope="class")
    def owner(self):
        email = seed_verified_user("shopowner", "Shopify Alpha")
        response = login(email)
        assert response.status_code == 200, response.text
        return {"email": email, **response.json()}

    @pytest.fixture(scope="class")
    def viewer(self):
        email = seed_verified_user("shopviewer", "Shopify Viewer Home")
        response = login(email)
        assert response.status_code == 200, response.text
        return {"email": email, **response.json()}

    def test_shopify_endpoints_require_authentication(self):
        response = requests.post(f"{API}/shopify/install", json={"shop_domain": "qa.myshopify.com"}, timeout=30)
        assert response.status_code == 401
        assert response.json()["code"] == "AUTH-003"

        status = requests.get(f"{API}/shopify/status", timeout=30)
        assert status.status_code == 401
        assert status.json()["code"] == "AUTH-003"

        disconnected = requests.delete(f"{API}/shopify/disconnect", timeout=30)
        assert disconnected.status_code == 401
        assert disconnected.json()["code"] == "AUTH-003"

    def test_shopify_requires_connect_permission(self, owner, viewer):
        """VIEWER lacks shopify.connect -> AUTHZ-001 (RBAC enforced server-side)."""
        invitee_email = seed_verified_user("shopviewer2", "Invitee Home")
        headers = auth_headers(owner["access_token"])
        invitation = requests.post(
            f"{API}/workspaces/invitations",
            json={"email": invitee_email, "role": "VIEWER"},
            headers=headers,
            timeout=30,
        )
        assert invitation.status_code == 201
        invite_token = None
        body = db.outbound_email.find_one(
            {"to_email": invitee_email, "template": "WORKSPACE_INVITATION"}, sort=[("created_at", -1)]
        )
        assert body, "no invitation email recorded"
        marker = "token="
        start = body["body"].index(marker) + len(marker)
        invite_token = body["body"][start:].split()[0].strip()

        invitee_login = login(invitee_email)
        assert invitee_login.status_code == 200, invitee_login.text
        invitee_headers = auth_headers(invitee_login.json()["access_token"])
        accepted = requests.post(
            f"{API}/workspaces/invitations/accept", json={"token": invite_token}, headers=invitee_headers, timeout=30
        )
        assert accepted.status_code == 200
        switched = requests.post(
            f"{API}/workspaces/{owner['workspace']['id']}/switch", headers=invitee_headers, timeout=30
        )
        assert switched.status_code == 200
        viewer_token = switched.json()["access_token"]

        install = requests.post(
            f"{API}/shopify/install",
            json={"shop_domain": "qa.myshopify.com"},
            headers=auth_headers(viewer_token),
            timeout=30,
        )
        assert install.status_code == 403
        assert install.json()["code"] == "AUTHZ-001"

    def test_install_rejects_invalid_shop_domain(self, owner):
        response = requests.post(
            f"{API}/shopify/install",
            json={"shop_domain": "https://evil.example.com"},
            headers=auth_headers(owner["access_token"]),
            timeout=30,
        )
        assert response.status_code == 400
        assert response.json()["code"] == "VALIDATION-001"

    def test_install_returns_external_001_when_unconfigured(self, owner):
        """Without Shopify Partner credentials the OAuth flow is unavailable."""
        response = requests.post(
            f"{API}/shopify/install",
            json={"shop_domain": "qa.myshopify.com"},
            headers=auth_headers(owner["access_token"]),
            timeout=30,
        )
        assert response.status_code == 503
        assert response.json()["code"] == "EXTERNAL-001"

    def test_callback_returns_external_001_when_unconfigured(self, owner):
        params = {
            "code": "abc123",
            "state": "state-nonce-1234567890",
            "shop": "qa.myshopify.com",
            "hmac": "deadbeef",
            "timestamp": "1700000000",
        }
        response = requests.get(f"{API}/shopify/callback", params=params, headers=auth_headers(owner["access_token"]), timeout=30)
        assert response.status_code == 503
        assert response.json()["code"] == "EXTERNAL-001"

    def test_status_reports_disconnected_when_no_connection(self, owner):
        response = requests.get(f"{API}/shopify/status", headers=auth_headers(owner["access_token"]), timeout=30)
        assert response.status_code == 200
        body = response.json()
        assert body["connected"] is False
        assert body["connection"] is None

    def test_disconnect_when_not_connected_returns_shopify_006(self, owner):
        response = requests.delete(f"{API}/shopify/disconnect", headers=auth_headers(owner["access_token"]), timeout=30)
        assert response.status_code == 404
        assert response.json()["code"] == "SHOPIFY-006"

    def test_seeded_connection_status_disconnect_and_audit(self, owner):
        """Status/disconnect work without credentials; the token is never exposed."""
        workspace_id = owner["workspace"]["id"]
        connection_id = seed_shopify_connection(workspace_id, "qa-store.myshopify.com")
        headers = auth_headers(owner["access_token"])

        status = requests.get(f"{API}/shopify/status", headers=headers, timeout=30)
        assert status.status_code == 200
        body = status.json()
        assert body["connected"] is True
        assert body["connection"]["id"] == connection_id
        assert body["connection"]["shop_domain"] == "qa-store.myshopify.com"
        assert "access_token" not in body["connection"]
        assert "access_token_encrypted" not in body["connection"]

        disconnected = requests.delete(f"{API}/shopify/disconnect", headers=headers, timeout=30)
        assert disconnected.status_code == 200
        assert disconnected.json()["message"] == "Shopify store disconnected."

        after = requests.get(f"{API}/shopify/status", headers=headers, timeout=30)
        assert after.json()["connected"] is False

        audit = db.audit_log.count_documents(
            {"workspace_id": workspace_id, "action": "SHOPIFY_DISCONNECTED", "resource_id": connection_id}
        )
        assert audit >= 1

    def test_oauth_state_ttl_index_exists(self):
        indexes = db.shopify_oauth_state.index_information()
        assert "ttl_shopify_oauth_state" in indexes
        assert indexes["ttl_shopify_oauth_state"]["expireAfterSeconds"] == 0

    def test_duplicate_install_prevented_when_configured(self, owner):
        """Requires Shopify credentials; skipped until they are configured."""
        if not os.environ.get("SHOPIFY_API_KEY") or not os.environ.get("SHOPIFY_API_SECRET"):
            pytest.skip("Shopify credentials not configured — duplicate-install prevention cannot be verified")
        workspace_id = owner["workspace"]["id"]
        seed_shopify_connection(workspace_id, "qa-store.myshopify.com")
        response = requests.post(
            f"{API}/shopify/install",
            json={"shop_domain": "qa-store.myshopify.com"},
            headers=auth_headers(owner["access_token"]),
            timeout=30,
        )
        assert response.status_code == 409
        assert response.json()["code"] == "SHOPIFY-005"