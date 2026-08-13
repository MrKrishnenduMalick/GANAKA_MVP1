"""Milestone 1 integration tests — Authentication & Workspace.

Runs against the live preview deployment (the same surface the frontend uses).
Email tokens are read from the `outbound_email` delivery ledger, because no SMTP
transport is configured in this environment.
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


def latest_email(to_email: str, template: str) -> dict:
    doc = db.outbound_email.find_one({"to_email": to_email, "template": template}, sort=[("created_at", -1)])
    assert doc, f"no {template} email recorded for {to_email}"
    return doc


def token_from_email(to_email: str, template: str) -> str:
    body = latest_email(to_email, template)["body"]
    marker = "token="
    start = body.index(marker) + len(marker)
    return body[start:].split()[0].strip()


def login(email: str, password: str = PASSWORD) -> requests.Response:
    """Login, tolerating the per-IP rate limit that protects this endpoint."""
    response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    if response.status_code == 429:
        time.sleep(61)
        response = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    return response


def register(email: str, workspace_name: str | None = None, password: str = PASSWORD) -> requests.Response:
    payload = {"email": email, "password": password, "full_name": "QA Person"}
    if workspace_name:
        payload["workspace_name"] = workspace_name
    response = requests.post(f"{API}/auth/register", json=payload, timeout=30)
    if response.status_code == 429:
        pytest.skip("registration rate limit (5/hour per IP) already consumed on this runner")
    return response


def seed_verified_user(prefix: str, workspace_name: str) -> str:
    """Create an ACTIVE user + owned workspace directly in MongoDB.

    Registration is rate limited to 5/hour per IP by design, so fixtures seed
    accounts instead of burning that budget; the HTTP registration path is still
    covered by TestRegistrationAndLogin. Role permissions come from the
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


def auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


class TestPlatform:
    def test_health_is_public_and_up(self):
        response = requests.get(f"{API}/health", timeout=30)
        assert response.status_code == 200
        assert response.json()["status"] == "UP"

    def test_protected_endpoint_requires_authentication(self):
        response = requests.get(f"{API}/auth/me", timeout=30)
        assert response.status_code == 401
        body = response.json()
        assert body["code"] == "AUTH-003"
        assert set(["timestamp", "status", "code", "message", "path", "requestId"]).issubset(body)


class TestRegistrationAndLogin:
    def test_weak_password_is_rejected_by_policy(self):
        response = register(unique_email("weak"), password="short1A!")
        assert response.status_code == 400
        assert response.json()["code"] == "AUTH-010"

    def test_duplicate_registration_is_indistinguishable(self):
        email = seed_verified_user("dupe", "Dupe Workspace")
        first = register(email)
        assert first.status_code == 201
        assert first.json()["message"] == "Check your email to verify your account."
        # The existing account is warned instead of a duplicate being created.
        assert latest_email(email, "REGISTER_COLLISION")
        assert db.user.count_documents({"email": email}) == 1

    def test_registration_verification_and_login(self):
        email = unique_email("newjoiner")
        created = register(email, workspace_name="QA Brand")
        assert created.status_code == 201, created.text

        blocked = login(email)
        assert blocked.status_code == 403
        assert blocked.json()["code"] == "AUTH-004"

        verified = requests.get(
            f"{API}/auth/verify-email", params={"token": token_from_email(email, "VERIFY_EMAIL")}, timeout=30
        )
        assert verified.status_code == 200

        session = requests.Session()
        response = session.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD}, timeout=30)
        if response.status_code == 429:
            time.sleep(61)
            response = session.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD}, timeout=30)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["workspace"]["name"] == "QA Brand"
        assert body["workspace"]["role"] == "OWNER"
        assert len(body["permissions"]) == 16
        assert "ganaka_refresh_token" in session.cookies.get_dict()

        me = session.get(f"{API}/auth/me", headers=auth_headers(body["access_token"]), timeout=30)
        assert me.status_code == 200
        assert me.json()["user"]["email"] == email

        first_refresh_cookie = session.cookies.get("ganaka_refresh_token")
        rotated = session.post(f"{API}/auth/refresh", timeout=30)
        assert rotated.status_code == 200
        assert session.cookies.get("ganaka_refresh_token") != first_refresh_cookie
        assert rotated.json()["refresh_token"] != body["refresh_token"]

        sessions = session.get(f"{API}/auth/sessions", headers=auth_headers(rotated.json()["access_token"]), timeout=30)
        assert sessions.status_code == 200
        assert any(item["current"] for item in sessions.json())

        logged_out = session.post(
            f"{API}/auth/logout-all", headers=auth_headers(rotated.json()["access_token"]), timeout=30
        )
        assert logged_out.status_code == 200
        after = session.get(f"{API}/auth/me", headers=auth_headers(rotated.json()["access_token"]), timeout=30)
        assert after.status_code == 401
        assert after.json()["code"] == "AUTH-006"

    def test_password_reset_invalidates_sessions(self):
        email = seed_verified_user("reset", "Reset Workspace")
        requested = requests.post(f"{API}/auth/forgot-password", json={"email": email}, timeout=30)
        if requested.status_code == 429:
            pytest.skip("forgot-password rate limit (5/hour per IP) already consumed on this runner")
        assert requested.status_code == 200
        reset_token = token_from_email(email, "PASSWORD_RESET")
        new_password = "Ganaka#Reset2026y"
        response = requests.post(
            f"{API}/auth/reset-password", json={"token": reset_token, "password": new_password}, timeout=30
        )
        assert response.status_code == 200
        # single use
        replay = requests.post(
            f"{API}/auth/reset-password", json={"token": reset_token, "password": new_password}, timeout=30
        )
        assert replay.status_code == 400
        assert replay.json()["code"] == "AUTH-009"
        assert latest_email(email, "PASSWORD_CHANGED")

    def test_forgot_password_does_not_disclose_accounts(self):
        response = requests.post(
            f"{API}/auth/forgot-password", json={"email": unique_email("ghost")}, timeout=30
        )
        if response.status_code == 429:
            pytest.skip("forgot-password rate limit (5/hour per IP) already consumed on this runner")
        assert response.status_code == 200
        assert "If an account exists" in response.json()["message"]


class TestAccountLockout:
    def test_five_failures_lock_the_account(self):
        email = seed_verified_user("lock", "Lockout Workspace")
        failures = 0
        while failures < 5:
            attempt = requests.post(
                f"{API}/auth/login", json={"email": email, "password": "Wrong#Password123"}, timeout=30
            )
            if attempt.status_code == 429:
                time.sleep(61)
                continue
            assert attempt.status_code == 401, attempt.text
            failures += 1
        locked = login(email)
        assert locked.status_code == 403, locked.text
        assert locked.json()["code"] == "AUTH-005"
        assert latest_email(email, "ACCOUNT_LOCKED")
        user = db.user.find_one({"email": email})
        assert user["locked_until"] is not None


class TestWorkspaceAndRbac:
    @pytest.fixture(scope="class")
    def owner(self):
        email = seed_verified_user("wsowner", "Isolation Alpha")
        response = login(email)
        assert response.status_code == 200, response.text
        return {"email": email, **response.json()}

    @pytest.fixture(scope="class")
    def outsider(self):
        email = seed_verified_user("outsider", "Isolation Beta")
        response = login(email)
        assert response.status_code == 200, response.text
        return {"email": email, **response.json()}

    def test_owner_sees_own_workspace_and_membership(self, owner):
        headers = auth_headers(owner["access_token"])
        detail = requests.get(f"{API}/workspaces/{owner['workspace']['id']}", headers=headers, timeout=30)
        assert detail.status_code == 200
        assert detail.json()["name"] == "Isolation Alpha"

        members = requests.get(
            f"{API}/workspaces/members", params={"page": 1, "size": 20}, headers=headers, timeout=30
        )
        assert members.status_code == 200
        assert members.json()["total"] == 1
        assert members.json()["items"][0]["roles"] == ["OWNER"]

    def test_cross_workspace_access_is_denied(self, owner, outsider):
        response = requests.get(
            f"{API}/workspaces/{owner['workspace']['id']}",
            headers=auth_headers(outsider["access_token"]),
            timeout=30,
        )
        assert response.status_code == 403
        assert response.json()["code"] == "WORKSPACE-007"

    def test_workspace_id_is_never_taken_from_the_client(self, owner, outsider):
        """Even a member listing request cannot be redirected to another tenant."""
        members = requests.get(
            f"{API}/workspaces/members",
            params={"workspace_id": owner["workspace"]["id"]},
            headers=auth_headers(outsider["access_token"]),
            timeout=30,
        )
        assert members.status_code == 200
        emails = [item["email"] for item in members.json()["items"]]
        assert emails == [outsider["email"]]

    def test_default_roles_and_permission_catalog(self, owner):
        headers = auth_headers(owner["access_token"])
        roles = requests.get(f"{API}/roles", params={"size": 100}, headers=headers, timeout=30)
        assert roles.status_code == 200
        names = {item["name"] for item in roles.json()["items"]}
        assert names == {"OWNER", "ADMIN", "FINANCE", "ACCOUNTANT", "VIEWER"}
        owner_role = next(item for item in roles.json()["items"] if item["name"] == "OWNER")
        viewer_role = next(item for item in roles.json()["items"] if item["name"] == "VIEWER")
        assert len(owner_role["permissions"]) == 16
        assert sorted(viewer_role["permissions"]) == ["dashboard.read", "report.read", "workspace.read"]

        permissions = requests.get(f"{API}/permissions", params={"size": 100}, headers=headers, timeout=30)
        assert permissions.status_code == 200
        assert permissions.json()["total"] == 16

    def test_custom_roles_require_a_paid_plan(self, owner):
        response = requests.post(
            f"{API}/roles",
            json={"name": "AUDITOR", "permissions": ["report.read"]},
            headers=auth_headers(owner["access_token"]),
            timeout=30,
        )
        assert response.status_code == 403
        assert response.json()["code"] == "AUTHZ-001"

    def test_invitation_lifecycle_and_role_enforcement(self, owner):
        headers = auth_headers(owner["access_token"])
        invitee_email = seed_verified_user("viewer", "Invitee Home")

        invitation = requests.post(
            f"{API}/workspaces/invitations",
            json={"email": invitee_email, "role": "VIEWER"},
            headers=headers,
            timeout=30,
        )
        assert invitation.status_code == 201
        assert invitation.json()["status"] == "PENDING"

        duplicate = requests.post(
            f"{API}/workspaces/invitations",
            json={"email": invitee_email, "role": "VIEWER"},
            headers=headers,
            timeout=30,
        )
        assert duplicate.status_code in (201, 409)

        invite_token = token_from_email(invitee_email, "WORKSPACE_INVITATION")
        invitee_login = login(invitee_email)
        assert invitee_login.status_code == 200, invitee_login.text
        invitee_headers = auth_headers(invitee_login.json()["access_token"])

        accepted = requests.post(
            f"{API}/workspaces/invitations/accept", json={"token": invite_token}, headers=invitee_headers, timeout=30
        )
        assert accepted.status_code == 200
        assert accepted.json()["role"] == "VIEWER"

        replayed = requests.post(
            f"{API}/workspaces/invitations/accept", json={"token": invite_token}, headers=invitee_headers, timeout=30
        )
        assert replayed.status_code == 400
        assert replayed.json()["code"] == "WORKSPACE-004"

        switched = requests.post(
            f"{API}/workspaces/{owner['workspace']['id']}/switch", headers=invitee_headers, timeout=30
        )
        assert switched.status_code == 200
        viewer_token = switched.json()["access_token"]
        assert switched.json()["workspace"]["role"] == "VIEWER"
        assert set(switched.json()["permissions"]) == {"dashboard.read", "report.read", "workspace.read"}

        forbidden = requests.post(
            f"{API}/workspaces/invitations",
            json={"email": unique_email("blocked"), "role": "VIEWER"},
            headers=auth_headers(viewer_token),
            timeout=30,
        )
        assert forbidden.status_code == 403
        assert forbidden.json()["code"] == "AUTHZ-001"

        cannot_update = requests.patch(
            f"{API}/workspaces/{owner['workspace']['id']}",
            json={"name": "Hijacked"},
            headers=auth_headers(viewer_token),
            timeout=30,
        )
        assert cannot_update.status_code == 403

    def test_owner_can_update_workspace_and_settings(self, owner):
        headers = auth_headers(owner["access_token"])
        workspace_id = owner["workspace"]["id"]
        updated = requests.patch(
            f"{API}/workspaces/{workspace_id}",
            json={"name": "Isolation Alpha Renamed", "currency": "INR"},
            headers=headers,
            timeout=30,
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Isolation Alpha Renamed"

        settings = requests.patch(
            f"{API}/workspaces/{workspace_id}/settings",
            json={"reconciliation_amount_tolerance": 1.5, "settlement_match_window_days": 20},
            headers=headers,
            timeout=30,
        )
        assert settings.status_code == 200
        assert settings.json()["reconciliation_amount_tolerance"] == 1.5
        assert settings.json()["settlement_match_window_days"] == 20

        out_of_bounds = requests.patch(
            f"{API}/workspaces/{workspace_id}/settings",
            json={"reconciliation_amount_tolerance": 9},
            headers=headers,
            timeout=30,
        )
        assert out_of_bounds.status_code == 400
        assert out_of_bounds.json()["code"] == "VALIDATION-001"

    def test_owner_cannot_be_removed(self, owner):
        headers = auth_headers(owner["access_token"])
        members = requests.get(f"{API}/workspaces/members", headers=headers, timeout=30).json()["items"]
        owner_member = next(item for item in members if item["is_owner"])
        response = requests.delete(f"{API}/workspaces/members/{owner_member['id']}", headers=headers, timeout=30)
        assert response.status_code == 403
        assert response.json()["code"] == "WORKSPACE-006"

    def test_mutations_are_audited(self, owner):
        count = db.audit_log.count_documents(
            {"workspace_id": owner["workspace"]["id"], "action": {"$in": ["WORKSPACE_CREATED", "MEMBER_INVITED"]}}
        )
        assert count >= 2


class TestGoogleSignIn:
    def test_google_login_is_disabled_without_credentials(self):
        response = requests.post(f"{API}/auth/google", json={"id_token": "not-a-real-token"}, timeout=30)
        assert response.status_code == 503
        assert response.json()["code"] == "EXTERNAL-001"
