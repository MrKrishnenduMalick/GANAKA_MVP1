# 19_COMPLIANCE_AND_PRIVACY.md

---
document:
  id: DOC-019
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

module:

id:

MOD-COMPLIANCE

owner:

PLATFORM

---

goal:

Protect customer data.

Ensure regulatory compliance.

Maintain privacy.

Provide secure data governance.

---

SUPPORTED_COMPLIANCE

DPDP_INDIA

GDPR_READY

SOC2_READY

ISO27001_READY

PCI_AWARE

---

DATA_CLASSIFICATION

PUBLIC

↓

INTERNAL

↓

CONFIDENTIAL

↓

RESTRICTED

↓

SECRET

---

DATA_TYPES

Customer

Workspace

Orders

Payments

Settlements

Invoices

Reports

Audit

Authentication

API Keys

Access Tokens

Refresh Tokens

Logs

---

PII

Name

Email

Phone

Business Address

GST Number

Billing Address

IP Address

---

SENSITIVE_DATA

JWT

OAuth Tokens

API Keys

Secrets

Encryption Keys

Database Credentials

Webhook Secrets

---

DATA_OWNERSHIP

Customer owns business data.

Platform processes data.

Platform never sells customer data.

Customer may export data anytime.

Customer may request deletion.

---

DATA_RETENTION

Audit Logs

7 Years

---

Application Logs

90 Days

---

Metrics

180 Days

---

OAuth Tokens

Until Revoked

---

Inactive Workspace

30 Days

After Deletion Request

---

Deleted Workspace Backup

30 Days

---

ENCRYPTION

AES-256

At Rest

---

TLS 1.3

In Transit

---

bcrypt

Passwords

---

JWT

Signed

---

ACCESS_CONTROL

RBAC

Least Privilege

MFA Required

Session Expiration

Audit Required

---

CONSENT

Accept Privacy Policy

Accept Terms

Cookie Consent

Marketing Consent

Email Verification

---

RIGHTS

Access Data

Export Data

Delete Data

Correct Data

Withdraw Consent

View Audit History

---

# GRIEVANCE_REDRESSAL (DPDP Act 2023 statutory requirement —
previously missing; a Data Fiduciary under DPDP must designate a
contact for grievances and respond within a defined window)

Grievance Officer

Ganaka designates a named Grievance Officer (business/legal
decision — a person or role, e.g. "Data Protection Officer",
recorded in company records, not left as "TBD" at launch since this
is a statutory requirement to operate lawfully under DPDP, not an
optional nice-to-have).

Contact Channel

A published grievance email/contact form, distinct from general
support (docs/18_SUPPORT_RUNBOOK.md), surfaced in the Privacy
Policy and in-app (Settings → Privacy → "Raise a Grievance").

Response SLA

Acknowledge within 48 hours. Substantive response within 30 days
(DPDP's own prescribed grievance-redressal timeline).

Scope

Grievances about consent handling, data access/correction/deletion
requests not fulfilled as expected, or any DPDP-rights-related
complaint — distinct from ordinary product support tickets, and
tracked in its own `grievances` table (grievance_id, workspace_id,
user_id, category, description, status, filed_at,
acknowledged_at, resolved_at) so response-time SLAs are auditable
per RULE below, not merely a promise in the Privacy Policy text.

Validation

Reject any implementation of the Rights/Consent flows above without
a corresponding grievance escalation path — a user whose deletion
request appears stuck must have a defined next step, not a dead end.

---

# CONSENT_WITHDRAWAL_EFFECTS (previously "Withdraw Consent" was
listed as a right with no defined effect)

Marketing Consent Withdrawn

Immediately suppress all marketing-category notifications
(implementation/10_NOTIFICATION_SYSTEM.md NOTIFICATION_TYPES —
transactional notifications, e.g. security/billing alerts, are
never gated by marketing consent and continue regardless).

Cookie Consent Withdrawn (non-essential cookies only — essential/
session cookies required for the app to function are not subject
to withdrawal, standard cookie-consent practice)

Disable non-essential analytics/tracking cookies for that user's
session going forward; does not retroactively delete already-
collected analytics data (that is governed by DATA_RETENTION, a
separate concern from consent-for-future-collection).

Validation

Reject any implementation where withdrawing marketing consent still
results in a marketing notification being sent.

---

WORKFLOW

Customer Requests Export

↓

Verify Identity

↓

Generate Export

↓

Encrypt Archive

↓

Notify Customer

↓

Expire Download Link

---

WORKFLOW

Customer Requests Deletion

↓

Verify Identity

↓

Verify Ownership

↓

Soft Delete

↓

Retention Countdown

↓

Permanent Delete

↓

Audit

---

PRIVACY_RULES

No Plaintext Passwords

No Plaintext Tokens

No Plaintext Secrets

No Cross Tenant Access

No Unauthorized Export

No Audit Modification

---

SECURITY_REQUIREMENTS

HTTPS Only

Secure Cookies

CSRF Protection

XSS Protection

SQL Injection Protection

Rate Limiting

Input Validation

Output Encoding

Secret Rotation

---

AUDIT

Login

Logout

Password Reset

MFA Reset

Workspace Created

Workspace Deleted

Subscription Updated

Admin Action

Data Export

Data Deletion

Permission Change

Role Change

---

EXPORT_FORMATS

CSV

JSON

ZIP

PDF Reports

---

COOKIE_TYPES

Essential

Analytics

Performance

Marketing

---

THIRD_PARTY_SERVICES

Shopify

Razorpay

Supabase

Resend

Cloudflare

---

DATA_TRANSFER

Encrypted

Authenticated

Audited

Verified

---

INCIDENT_RESPONSE

Identify

↓

Contain

↓

Investigate

↓

Recover

↓

Notify

↓

Postmortem

---

BREACH_NOTIFICATION

Internal

Immediate

---

Affected Customers

Without Undue Delay

---

Audit Record

Mandatory

---

API

GET

/privacy

GET

/terms

GET

/data/export

POST

/data/delete

GET

/consent

POST

/consent

---

METRICS

Export Requests

Deletion Requests

Consent Rate

Failed Auth

Unauthorized Access

Security Incidents

Audit Entries

---

EVENTS

DATA_EXPORTED

DATA_DELETED

CONSENT_UPDATED

SECURITY_INCIDENT

ACCESS_DENIED

TOKEN_ROTATED

PASSWORD_RESET

---

COMPLIANCE_CHECKS

Encryption Enabled

Audit Enabled

RBAC Enabled

MFA Enabled

HTTPS Enabled

Secrets Encrypted

Backups Encrypted

---

CURSOR_RULES

Never store plaintext passwords.

Never store plaintext API keys.

Never expose OAuth tokens.

Never bypass RBAC.

Never disable audit logging.

Every sensitive operation must be audited.

Every export requires ownership verification.

Every deletion requires confirmation.

Every cross-tenant request must be denied.

---

ACCEPTANCE

✓ Data Export Works

✓ Data Deletion Works

✓ Audit Created

✓ Encryption Verified

✓ RBAC Enforced

✓ HTTPS Enforced

✓ Secrets Protected

✓ Compliance Checks Pass

---

STATUS

COMPLETE

READY_FOR_CURSOR

TRUE