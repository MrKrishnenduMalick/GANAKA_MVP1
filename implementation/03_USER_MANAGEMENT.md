# implementation/03_USER_MANAGEMENT.md

---
document:
  id: IMP-003
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

module:

id:

USER_MANAGEMENT

owner:

PLATFORM

---

goal:

Manage workspace users, invitations, profiles, lifecycle, preferences and account administration.

---

CORE_ENTITIES

User

Profile

WorkspaceMember

Invitation

Session

Preference

NotificationPreference

---

USER_FIELDS

Note: `users` is a workspace-independent identity table. It must
NEVER carry a `workspace_id` column — a user belongs to zero or
more workspaces via the separate `workspace_members` join entity
(see implementation/02_WORKSPACE_AND_RBAC.md), because BR-002
requires one user to belong to multiple workspaces with independent
per-workspace roles. Putting workspace_id directly on `users` would
make that structurally impossible. Role/permission context for a
request always comes from `workspace_members`, resolved at
authentication time (implementation/01_AUTHENTICATION.md ROLE_LOADING),
never from a column on `users`.

user_id

email

full_name

avatar_url

phone

timezone

language

status

created_at

updated_at

last_login_at

---

USER_STATUS

INVITED

↓

PENDING

↓

ACTIVE

↓

LOCKED

↓

DISABLED

↓

DELETED

---

PROFILE

Full Name

Avatar

Phone

Timezone

Language

Job Title

Department

Bio

---

PREFERENCES

Theme

Language

Timezone

Currency

Date Format

Email Notifications

Push Notifications

Digest Frequency

---

USER_TYPES

These are the workspace-scoped roles a user can hold, one per
workspace they belong to. This list must always match
implementation/02_WORKSPACE_AND_RBAC.md DEFAULT_ROLES exactly —
do not add or rename roles here.

Owner

Admin

Finance

Accountant

Viewer

Note: "Support User" is NOT a workspace role. Ganaka platform
support staff acting on a customer's behalf use the separate
internal admin role system defined in
docs/14_ADMIN_OPERATIONS.md (SUPPORT_ADMIN), which operates through
platform admin tooling, not through workspace membership. Never
create a workspace_members row for internal support staff.

---

MEMBERSHIP

Single User

↓

Multiple Workspaces Supported

↓

Independent Roles Per Workspace

---

INVITATION_FLOW

Invite User

↓

Validate Email

↓

Generate Token

↓

Send Email

↓

Accept Invitation

↓

Join Workspace

↓

Assign Role

↓

Audit

---

PROFILE_UPDATE

Validate Input

↓

Update Profile

↓

Refresh Cache

↓

Audit

---

CHANGE_EMAIL

Verify Password

↓

New Email Verification

↓

Verify Token

↓

Update Email

↓

Invalidate Sessions

↓

Audit

---

CHANGE_PASSWORD

Verify Current Password

↓

Validate Policy

↓

Hash Password

↓

Invalidate Sessions

↓

Audit

---

CHANGE_AVATAR

Upload Image

↓

Validate Type

↓

Optimize

↓

Store

↓

Update Profile

↓

Audit

---

USER_SEARCH

Email

Name

Role

Status

Department

Created Date

---

BULK_OPERATIONS

Invite Users

Remove Users

Assign Roles

Deactivate Users

Export Users

---

USER_EXPORT

CSV

Excel

JSON

---

USER_IMPORT

CSV

Validation

Duplicate Detection

Role Assignment

Audit

---

NOTIFICATION_SETTINGS

Security Alerts

Billing Alerts

Reports

Marketing

System Updates

Weekly Summary

---

SECURITY

Email Verified Required

Password Policy Enforced

RBAC Required

Workspace Isolation

Audit Required

---

API

GET

/api/v1/users

POST

/api/v1/users

GET

/api/v1/users/{id}

PATCH

/api/v1/users/{id}

DELETE

/api/v1/users/{id}

GET

/api/v1/users/profile

PATCH

/api/v1/users/profile

POST

/api/v1/users/change-email

POST

/api/v1/users/change-password

POST

/api/v1/users/avatar

POST

/api/v1/users/import

GET

/api/v1/users/export

---

DATABASE

users

profiles

workspace_members

user_preferences

notification_preferences

user_import_jobs

user_export_jobs

audit_logs

---

EVENTS

USER_CREATED

USER_UPDATED

USER_DELETED

USER_LOCKED

USER_DISABLED

PROFILE_UPDATED

PASSWORD_CHANGED

EMAIL_CHANGED

AVATAR_UPDATED

USER_IMPORTED

USER_EXPORTED

---

ERRORS

USER_NOT_FOUND

EMAIL_ALREADY_EXISTS

INVALID_ROLE

INVALID_AVATAR

PROFILE_UPDATE_FAILED

PASSWORD_POLICY_FAILED

IMPORT_FAILED

EXPORT_FAILED

---

METRICS

Total Users

Active Users

Invitations Sent

Invitation Acceptance Rate

Profile Completion Rate

Password Changes

Failed Invitations

Imported Users

Exported Users

---

ACCEPTANCE

✓ Invite User

✓ Accept Invitation

✓ Update Profile

✓ Change Email

✓ Change Password

✓ Upload Avatar

✓ Import Users

✓ Export Users

✓ Update Preferences

✓ Notification Settings

✓ Audit Generated

---

CURSOR_RULES

Every user belongs to at least one workspace.

Never allow duplicate email addresses.

Always verify workspace membership.

Always validate RBAC before modifications.

Always invalidate sessions after credential changes.

Always optimize uploaded avatars.

Never expose internal user IDs externally when avoidable.

Every profile update must be audited.

Every import/export must be auditable.

Never bypass workspace isolation.

---

STATUS

COMPLETE

READY_FOR_CURSOR

TRUE