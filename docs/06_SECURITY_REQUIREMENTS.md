# 06_SECURITY_REQUIREMENTS.md

# Ganaka Security Requirements

Version: 1.0.0

Status: Approved

---

# PURPOSE

This document defines all security requirements for Ganaka.

Every authentication flow, API, database operation, and user action must comply with these rules.

Security is mandatory and cannot be bypassed.

---

# SECURITY MODEL

Authentication

JWT + Refresh Token

Authorization

Role-Based Access Control (RBAC)

Tenant Isolation

Workspace-Based

Transport

HTTPS Only

Password Storage

BCrypt

Session

Stateless

---

# RULE SEC-001

Requirement

Every protected endpoint must require authentication.

Applies To

- REST APIs
- Admin APIs
- Dashboard APIs
- Internal APIs

Forbidden

Anonymous access.

Validation

Reject unauthenticated requests.

---

# RULE SEC-002

Requirement

JWT access tokens must be validated on every request.

Validation Includes

- Signature
- Expiration
- Issuer
- Subject
- Workspace

Validation

Reject invalid tokens.

---

# RULE SEC-003

Requirement

Refresh Tokens must be securely stored and revocable.

Forbidden

Permanent refresh tokens.

Validation

Support token revocation.

---

# RULE SEC-004

Requirement

Passwords must be hashed using BCrypt.

Forbidden

- Plain text
- SHA-1
- MD5

Validation

Reject insecure hashing.

---

# RULE SEC-005

Requirement

Passwords must satisfy

- Minimum 12 characters
- Uppercase
- Lowercase
- Number
- Special Character

Validation

Reject weak passwords.

---

# RULE SEC-006

Requirement

Role-Based Access Control (RBAC) is mandatory.

Default Roles

The canonical list of default workspace roles and their permission
matrix is defined ONCE in implementation/02_WORKSPACE_AND_RBAC.md
(DEFAULT_ROLES / OWNER / ADMIN / FINANCE / ACCOUNTANT / VIEWER
sections). Do not restate role names here — this avoids the role
lists silently drifting apart across documents.

Validation

Reject unauthorized actions.

Reject any implementation that defines workspace role names not
present in implementation/02_WORKSPACE_AND_RBAC.md.

---

# RULE SEC-007

Requirement

Workspace isolation must be enforced for every database query.

Forbidden

Cross-workspace data access.

Validation

Reject data leakage.

---

# RULE SEC-008

Requirement

Every authenticated request must resolve

- User
- Workspace
- Role

Validation

Reject incomplete identity context.

---

# RULE SEC-009

Requirement

Sensitive configuration must be stored outside source code.

Examples

- API Keys
- JWT Secret
- Database Password
- SMTP Credentials

Forbidden

Hardcoded secrets.

Validation

Reject embedded credentials.

---

# RULE SEC-010

Requirement

All communication must use HTTPS.

Forbidden

HTTP

Validation

Reject insecure transport.

---

# RULE SEC-011

Requirement

Every input must be validated before processing.

Validation Includes

- Length
- Type
- Format
- Range
- Enum
- UUID

Validation

Reject invalid input.

---

# RULE SEC-012

Requirement

Prevent common web attacks.

Minimum Protection

- SQL Injection
- XSS
- CSRF (where applicable)
- Command Injection
- Path Traversal

Validation

Security review required.

---

# RULE SEC-013

Requirement

Uploaded files must be validated.

Validation Includes

- MIME Type
- Extension
- Size
- Malware Scan (future)

Forbidden

Executable uploads.

Validation

Reject unsafe files.

---

# RULE SEC-014

Requirement

Sensitive fields must never appear in API responses.

Examples

- Password
- Hash
- Secret
- Refresh Token
- API Key

Validation

Reject sensitive response payloads.

---

# RULE SEC-015

Requirement

Financial operations require audit logging.

Audit Includes

- User
- Workspace
- Timestamp
- Action
- Entity
- Result

Validation

Reject unaudited financial changes.

---

# RULE SEC-016

Requirement

Failed authentication attempts must be logged.

Validation

Generate security audit entry.

---

# RULE SEC-017

Requirement

Rate limiting must protect

- Login
- Registration
- Password Reset
- Public APIs
- Webhooks

Validation

Reject unlimited requests.

---

# RULE SEC-018

Requirement

Error responses must never expose internal implementation details.

Forbidden

- Stack Trace
- SQL
- File Paths
- Internal Exceptions

Validation

Return standardized errors only.

---

# RULE SEC-019

Requirement

Dependencies must be actively maintained.

Forbidden

Known vulnerable libraries.

Validation

Run dependency vulnerability scans.

---

# RULE SEC-020

Requirement

Security review is mandatory before release.

Review Includes

✓ Authentication

✓ Authorization

✓ Input Validation

✓ Secrets

✓ Audit Logs

✓ Workspace Isolation

✓ Rate Limiting

✓ Secure Headers

Validation

Deployment blocked until security review passes.

---

# SECURITY REVIEW CHECKLIST

Before release verify

✓ Authentication works

✓ Authorization works

✓ JWT validated

✓ Workspace isolation enforced

✓ Password hashing correct

✓ Secrets externalized

✓ HTTPS enabled

✓ Input validated

✓ Audit logging active

✓ No sensitive data exposed

---

# RULE SEC-021

Requirement

Webhook HMAC Verification (Shopify + Razorpay)

Detail

Every inbound webhook must have its HMAC signature verified against
the raw, unparsed request body BEFORE any JSON parsing or business
logic executes. Use a constant-time comparison
(`MessageDigest.isEqual` in Java / `hmac.compare_digest` in Python —
never `==` or `.equals()`, which are timing-attack-vulnerable).
Shopify: `X-Shopify-Hmac-Sha256` header, HMAC-SHA256 over the raw
body with the app's webhook secret. Razorpay: `X-Razorpay-Signature`
header, HMAC-SHA256 over the raw body with the merchant's configured
webhook secret (implementation/05_RAZORPAY.md).

Validation

Reject any webhook handler that parses the body before verifying
the signature.

Reject any signature comparison that is not constant-time.

---

# RULE SEC-022

Requirement

Webhook Replay Protection

Detail

Every verified webhook event must be checked against a dedup store
(Redis, key = `webhook:{source}:{event_id}`, TTL = 7 days) before
processing. If the event_id has already been processed, return 200
OK immediately without reprocessing (webhooks are frequently
redelivered by both Shopify and Razorpay on transient failures — the
handler must be idempotent, not merely fast to reject).

Validation

Reject any webhook handler without a dedup check keyed on the
provider's own event/delivery ID.

---

# RULE SEC-023

Requirement

Webhook Timestamp Validation

Detail

Reject any webhook whose provider-supplied timestamp (Razorpay:
payload `created_at`; Shopify: no standard timestamp header, so
apply this check to Razorpay only, and rely on SEC-022's replay
store for Shopify) differs from server time by more than 5 minutes.
This bounds the window an intercepted-and-replayed signed payload
could be reused in, even before the dedup store is consulted.

Validation

Reject any webhook processed without a timestamp-skew check.

---

# RULE SEC-024

Requirement

Nonce Validation (internal service-to-service calls)

Detail

Every Core Platform → AI Service call
(docs/21_HYBRID_ARCHITECTURE.md) includes a unique per-request
nonce in the internal service JWT's `jti` claim. The AI Service
rejects any request whose `jti` has been seen within the token's
5-minute validity window (Redis dedup, same pattern as SEC-022),
preventing a captured internal token from being replayed even
within its short validity window.

Validation

Reject any internal-service JWT without a `jti` claim.

---

# RULE SEC-025

Requirement

Idempotency (client-initiated write operations)

Detail

Every state-changing public API endpoint that a client might
plausibly retry (payment-adjacent actions, workspace creation,
report generation, courier invoice upload) must accept an optional
`Idempotency-Key` header. If a request with a previously-seen key
(same workspace, same key, within 24 hours) arrives, return the
original response rather than re-executing the operation. Store
idempotency records in Redis or a dedicated `idempotency_keys`
table (key, workspace_id, request_hash, response_body, expires_at).
If the same key is reused with a DIFFERENT request body, reject with
`409 IDEMPOTENCY_KEY_CONFLICT` — never silently execute the new body
under the old key.

Validation

Reject any implementation that executes a duplicate write when a
matching Idempotency-Key is present.

---

# RULE SEC-026

Requirement

API Key Rotation (merchant-supplied Razorpay/Shopify credentials)

Detail

Workspace Owners/Admins can rotate their stored Razorpay API
Key/Secret or Shopify access token at any time via
`/api/v1/razorpay/connect` (re-submission) or Shopify OAuth
re-authorization, without downtime — the old credential remains
valid for in-flight requests for up to 60 seconds after a new one is
saved, then is discarded from memory/cache (never logged, never
retained beyond the encrypted `credentials` column, which is
overwritten, not versioned/kept in history).

Validation

Reject any implementation that stores more than the current active
credential in queryable form.

---

# RULE SEC-027

Requirement

Internal Secret Rotation (platform-owned secrets: JWT_SECRET,
INTERNAL_SERVICE_JWT_SECRET, database credentials, encryption keys)

Detail

All platform-owned secrets are rotated on a maximum 90-day schedule,
tracked in the secrets manager (see SEC-028), never hardcoded, never
committed. JWT_SECRET rotation must support a grace/overlap period
(dual-key verification: accept tokens signed by either the
previous or current key for up to the access-token TTL, 15 minutes,
after rotation) so in-flight sessions aren't force-logged-out on
every rotation.

Validation

Reject any secret with no rotation date/owner recorded in the
secrets manager.

---

# RULE SEC-028

Requirement

Key Management / Cloud KMS

Detail

All encryption-at-rest keys (used for AES256 encryption of stored
Shopify/Razorpay credentials, per implementation/00_FOUNDATION.md
and implementation/05_RAZORPAY.md) are managed via a cloud KMS
(e.g. the hosting provider's managed KMS — do not hand-roll key
storage in application config or environment variables for anything
beyond the KMS's own access credential). Application code never
sees a raw Data Encryption Key directly — it requests
encrypt/decrypt operations through the KMS client, or uses envelope
encryption (KMS-wrapped Data Encryption Keys stored alongside
ciphertext, unwrapped per-operation).

Validation

Reject any implementation that stores a raw encryption key in
application config, environment variables, or source control.

---

# RULE SEC-029

Requirement

Encryption Key Lifecycle

Detail

KMS keys used for encrypting merchant credentials are rotated
annually at minimum (KMS-managed automatic rotation where the
provider supports it). Data encrypted under a retired key version
remains decryptable (KMS retains prior key versions) until it is
re-encrypted under the current version — re-encryption happens
lazily, on next credential update, not as a bulk migration job that
touches every workspace's stored credentials at once.

Validation

Reject any implementation that makes old key versions permanently
undecryptable before all data under them has been re-encrypted.

---

# RULE SEC-030

Requirement

Audit Requirements For All Of The Above

Detail

Every webhook signature failure, replay rejection, timestamp
rejection, idempotency conflict, credential rotation, and secret
rotation event is written to `audit_logs` (implementation/11_PLATFORM.md
/ docs/14_ADMIN_OPERATIONS.md AUDIT patterns) — security-relevant
rejections are audit events in their own right, not just silently
dropped requests, since a spike in webhook signature failures, for
example, is itself a signal worth an Admin being able to see later.

Validation

Reject any implementation that fails a security check silently
without an audit_logs entry.

---

# THREAT MODEL MAPPING (OWASP / STRIDE)

This section maps existing rules above to standard threat-modeling
frameworks. It does not introduce new controls — it cross-references
SEC-001 through SEC-030 so reviewers and Cursor can verify framework
coverage without re-deriving it. If a mapped row has no rule number,
that is a real gap to close with a new SEC-0xx rule, not a documentation
omission.

## OWASP Top 10 (Web Application)

| OWASP Risk | Covered By |
|---|---|
| A01 Broken Access Control | SEC-006, SEC-007, SEC-008 |
| A02 Cryptographic Failures | SEC-004, SEC-028, SEC-029 |
| A03 Injection (SQLi/XSS/Command) | SEC-011, SEC-012 |
| A04 Insecure Design | SEC-006 (RBAC-by-default), SEC-025 (idempotency-by-design) |
| A05 Security Misconfiguration | SEC-009, SEC-010 |
| A06 Vulnerable/Outdated Components | SEC-019 |
| A07 Identification/Authentication Failures | SEC-001, SEC-002, SEC-003, SEC-005, SEC-016 |
| A08 Software/Data Integrity Failures | SEC-021 (HMAC), SEC-027 (secret rotation) |
| A09 Security Logging/Monitoring Failures | SEC-015, SEC-016, SEC-030 |
| A10 Server-Side Request Forgery (SSRF) | Gap — no rule currently restricts outbound requests triggered by user-supplied URLs (e.g. Shopify shop domain input, webhook callback URLs). Add SEC-031 requiring allowlist validation before Core Platform Service makes any outbound call built from user-supplied input. |

## OWASP API Security Top 10

| OWASP API Risk | Covered By |
|---|---|
| API1 Broken Object Level Authorization | SEC-007, SEC-008 |
| API2 Broken Authentication | SEC-001, SEC-002, SEC-003 |
| API3 Broken Object Property Level Authorization | SEC-014 |
| API4 Unrestricted Resource Consumption | SEC-017 |
| API5 Broken Function Level Authorization | SEC-006 |
| API6 Unrestricted Access to Sensitive Business Flows | SEC-017 (rate limiting), SEC-025 (idempotency) |
| API7 Server-Side Request Forgery | Gap — same as OWASP A10 above; see SEC-031 |
| API8 Security Misconfiguration | SEC-009, SEC-010, SEC-018 |
| API9 Improper Inventory Management | Gap — no rule requires a maintained internal API inventory distinguishing `/api/v1/*` (public), `/internal/v1/*` (service-to-service), and any deprecated versions. Add SEC-032 requiring docs/05_API_SPECIFICATION.md to list every endpoint's exposure tier and deprecation status.
| API10 Unsafe Consumption of APIs | SEC-021, SEC-022, SEC-023 (applies to Shopify/Razorpay as consumed APIs) |

## STRIDE (applied to the two-service Hybrid Architecture, docs/21_HYBRID_ARCHITECTURE.md)

| STRIDE Category | Primary Concern In Ganaka | Covered By |
|---|---|---|
| Spoofing | Forged internal service token between Core Platform and AI Service | SEC-024, docs/21_HYBRID_ARCHITECTURE.md AUTHENTICATION BETWEEN SERVICES |
| Tampering | Modified webhook payload from Shopify/Razorpay | SEC-021 |
| Repudiation | Financial action taken with no traceable actor | SEC-015, SEC-030 |
| Information Disclosure | Sensitive fields leaking via API responses or error messages | SEC-014, SEC-018 |
| Denial of Service | Login/webhook/public API flooding | SEC-017 |
| Elevation of Privilege | Cross-workspace access or role escalation | SEC-006, SEC-007, SEC-008 |

## New Rules Introduced By This Mapping

# RULE SEC-031

Requirement

Server-Side Request Forgery (SSRF) Protection.

Detail

Any outbound HTTP call the Core Platform Service makes where the
target host is derived, even partially, from user-supplied input
(Shopify shop domain during OAuth connect, any future custom
webhook-callback URL) must validate the resolved host against an
allowlist of expected domains (`*.myshopify.com` for Shopify,
Razorpay's documented API hosts) before the request is issued.
Reject requests to private/link-local IP ranges (RFC 1918,
169.254.0.0/16, 127.0.0.0/8) even if a hostname resolves there.

Validation

Reject any outbound call built from user-supplied input without a
prior allowlist/IP-range check.

---

# RULE SEC-032

Requirement

API Inventory Management.

Detail

docs/05_API_SPECIFICATION.md must list every endpoint's exposure
tier (`public /api/v1/*`, `internal /internal/v1/*`) and its status
(`active`, `deprecated`, `sunset-date`). Cursor must not add an
endpoint to either service without a corresponding inventory entry.

Validation

Reject any endpoint present in code but absent from the API
inventory.

---

# REFERENCES

Architecture

docs/03_ARCHITECTURE.md

API

docs/05_API_SPECIFICATION.md

Business Rules

docs/07_BUSINESS_RULES.md

Hybrid Architecture

docs/21_HYBRID_ARCHITECTURE.md

Implementation

implementation/

---

END OF DOCUMENT