# implementation/02_WORKSPACE_AND_RBAC.md

---
document:
  id: IMP-002
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

module:

id:

WORKSPACE_RBAC

owner:

PLATFORM

---

goal:

Implement secure multi-tenant workspace isolation, role-based access control,
permission management and organization ownership.

---

CORE_ENTITIES

Workspace

WorkspaceMember

Role

Permission

RolePermission

UserRole

Invitation

WorkspaceSettings

---

WORKSPACE

fields

workspace_id

name

slug

status

owner_id

plan

timezone

currency

created_at

updated_at

---

WORKSPACE_STATUS

ACTIVE

SUSPENDED

ARCHIVED

DELETED

---

WORKSPACE_TYPES

FREE

PRO

ENTERPRISE

---

DEFAULT_ROLES

OWNER

ADMIN

FINANCE

ACCOUNTANT

VIEWER

---

ROLE_HIERARCHY

OWNER

↓

ADMIN

↓

FINANCE

↓

ACCOUNTANT

↓

VIEWER

---

DEFAULT_PERMISSIONS

workspace.read

workspace.update

workspace.delete

workspace.settings

workspace.members

workspace.billing

dashboard.read

report.read

report.export

shopify.connect

razorpay.connect

finance.read

finance.write

reconciliation.run

notification.manage

admin.access

---

OWNER

All Permissions

---

ADMIN

All Except

Billing Delete

Workspace Delete

Owner Transfer

---

FINANCE

Billing

Reports

Finance

Reconciliation

---

ACCOUNTANT

Finance Read

Reports

Reconciliation Read

---

VIEWER

Dashboard Read

Reports Read

---

MEMBER_STATES

INVITED

↓

PENDING

↓

ACTIVE

↓

SUSPENDED

↓

REMOVED

---

INVITATION_FLOW

Owner

↓

Create Invitation

↓

Generate Secure Token

↓

Email Invitation

↓

Accept Invitation

↓

Assign Role

↓

Audit

---

TRANSFER_OWNERSHIP

Current Owner

↓

Permission Check

↓

New Owner Validation

↓

Transfer

↓

Update Roles

↓

Audit

---

WORKSPACE_SWITCH

Validate Membership

↓

Load Workspace

↓

Load Permissions

↓

Generate Context

↓

Refresh JWT Claims

---

TENANT_ISOLATION

Every Query Filtered By Workspace

Every Cache Key Scoped

Every Queue Job Scoped

Every Audit Scoped

Every Storage Object Scoped

Every API Scoped

---

AUTHORIZATION_FLOW

Authenticate

↓

Load Workspace

↓

Load Membership

↓

Load Roles

↓

Resolve Permissions

↓

Authorize

↓

Execute

↓

Audit

---

PERMISSION_CHECK

User

↓

Workspace

↓

Role

↓

Permission

↓

Grant

OR

Deny

---

CUSTOM_ROLES

Enabled

PRO

ENTERPRISE

---

Maximum Roles

50

---

Maximum Permissions Per Role

200

---

WORKSPACE_SETTINGS

Company Name

Timezone

Currency

Logo

Theme

Language

Notification Settings

Billing Settings

Security Settings

Reconciliation Settings (see implementation/07_RECONCILIATION_ENGINE.md
TOLERANCE_RULES for the exact semantics and bounds of each field)

- reconciliation_amount_tolerance (DECIMAL, default 0.00, max 5.00)
- settlement_match_window_days (INTEGER, default 15, max 45)

---

SECURITY_RULES

No Cross Workspace Access

Workspace Isolation Mandatory

Owner Cannot Remove Self

Owner Transfer Audited

Invitation Tokens Expire

Permission Validation Required

---

INVITATION_POLICY

Expiration

7 Days

Single Use

Email Bound

Workspace Bound

---

API

GET

/api/v1/workspaces

POST

/api/v1/workspaces

GET

/api/v1/workspaces/{id}

PATCH

/api/v1/workspaces/{id}

DELETE

/api/v1/workspaces/{id}

GET

/api/v1/workspaces/members

POST

/api/v1/workspaces/members

PATCH

/api/v1/workspaces/members/{id}

DELETE

/api/v1/workspaces/members/{id}

POST

/api/v1/workspaces/invitations

POST

/api/v1/workspaces/invitations/accept

POST

/api/v1/workspaces/{id}/switch (implements the WORKSPACE_SWITCH
flow above; validates membership, then returns a freshly issued
access token + refresh token scoped to the target workspace_id.
Previously this flow existed with no corresponding endpoint —
added here so it isn't left for the AI to invent.)

GET

/api/v1/roles

POST

/api/v1/roles

PATCH

/api/v1/roles/{id}

DELETE

/api/v1/roles/{id}

GET

/api/v1/permissions

---

DATABASE

workspaces

workspace_members

roles

permissions

role_permissions

user_roles

workspace_invitations

workspace_settings

audit_logs

---

EVENTS

WORKSPACE_CREATED

WORKSPACE_UPDATED

WORKSPACE_DELETED

WORKSPACE_SUSPENDED

MEMBER_INVITED

MEMBER_JOINED

MEMBER_REMOVED

ROLE_CREATED

ROLE_UPDATED

ROLE_DELETED

PERMISSION_GRANTED

PERMISSION_REVOKED

OWNERSHIP_TRANSFERRED

---

ERRORS

WORKSPACE_NOT_FOUND

MEMBER_ALREADY_EXISTS

INVALID_INVITATION

INVITATION_EXPIRED

ROLE_NOT_FOUND

PERMISSION_DENIED

OWNER_REQUIRED

CROSS_WORKSPACE_ACCESS_DENIED

---

METRICS

Workspace Count

Active Members

Invitations Sent

Invitation Acceptance Rate

Permission Checks

Authorization Failures

Workspace Switches

Role Count

---

ACCEPTANCE

✓ Create Workspace

✓ Update Workspace

✓ Suspend Workspace

✓ Invite Member

✓ Accept Invitation

✓ Remove Member

✓ Assign Role

✓ Create Custom Role

✓ Permission Validation

✓ Workspace Isolation

✓ Ownership Transfer

✓ Audit Generated

---

CURSOR_RULES

Every database query must include workspace_id.

Never allow cross-tenant data access.

Never trust frontend permissions.

Always validate membership before authorization.

Always resolve permissions server-side.

Always audit membership changes.

Always audit role changes.

Always audit ownership transfer.

Never allow ownerless workspaces.

Never hardcode permissions.

Never bypass RBAC.

---

STATUS

COMPLETE

READY_FOR_CURSOR

TRUE