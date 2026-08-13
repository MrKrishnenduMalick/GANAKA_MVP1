# implementation/01_AUTHENTICATION.md

---
document:
  id: IMP-001
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

module:

id:

AUTHENTICATION

owner:

PLATFORM

---

goal:

Provide secure authentication, authorization, session management,
identity verification and account security.

---

AUTH_METHODS

Email Password

Google OAuth

Magic Link

Refresh Token

---

IDENTITY

Primary

Email

---

Unique

Email

---

OPTIONAL

Phone

Profile Image

---

ACCOUNT_STATES

REGISTERED

↓

EMAIL_PENDING

↓

ACTIVE

↓

LOCKED

↓

DISABLED

↓

DELETED

---

LOGIN_FLOW

Email

↓

Password

↓

Validation

↓

Email Verified

↓

MFA (Future)

↓

JWT

↓

Refresh Token

↓

Audit

↓

Dashboard

---

GOOGLE_LOGIN

Google OAuth

↓

Verify Token (signature + audience + issuer)

↓

Require token's `email_verified` claim == true — reject login
otherwise (prevents a Google account with an unverified email from
impersonating an existing Ganaka user)

↓

ACCOUNT_LINKING_CHECK (see below)

↓

Create Workspace If New

↓

Generate JWT

↓

Audit

---

ACCOUNT_LINKING_CHECK (previously undefined — resolves account-takeover
ambiguity between email/password and Google sign-in on the same email)

Case 1: No existing user with this email

Create new user, `oauth_accounts` row, proceed.

Case 2: Existing user with this email, no linked Google account,
password-based account already ACTIVE

Do NOT silently log them in as that user. Require the user to
complete one of:
(a) log in with their existing password once and link Google from
Account Settings, or
(b) if they no longer have the password, go through the standard
password-reset flow first.

Reject the Google login attempt with `ACCOUNT_LINKING_REQUIRED`,
do not reveal in the error message whether the collision was due to
password vs Google account (avoid enumeration) — send an email to
the account's registered address instead, explaining a Google
sign-in attempt was made and linking instructions.

Case 3: Existing user, Google account already linked

Normal login.

---

REGISTER_ENUMERATION_PROTECTION (previously undefined)

If a registration attempt uses an email that already exists,
respond with the same generic success message used for a genuinely
new registration ("Check your email to verify your account"), and
silently send an "someone tried to register with your email —
if this wasn't you, reset your password" email to the existing
address instead of creating a duplicate account or returning an
"email already exists" error.

Validation

Reject any implementation that returns a distinguishable response
(status code, message, or timing) between "new registration" and
"email already registered."

PASSWORD_POLICY

Minimum 12 Characters (matches docs/06_SECURITY_REQUIREMENTS.md
RULE SEC-005 — this is the single canonical value, do not restate
a different number elsewhere)

Maximum 128 Characters

Uppercase Required

Lowercase Required

Number Required

Special Character Required

Common Password Blocked

---

PASSWORD_STORAGE

Algorithm

BCrypt

---

Never Store Plaintext

---

EMAIL_VERIFICATION

Required

Token Expiry

24 Hours

Single Use

---

PASSWORD_RESET

Email Verification

↓

Generate Secure Token

↓

15 Minute Expiry

↓

Reset Password

↓

Invalidate Sessions

↓

Audit

---

JWT

Algorithm

HS256

---

Access Token

15 Minutes

---

Refresh Token

30 Days

---

Claims

user_id

workspace_id

role

permissions

session_id

issued_at

expires_at

---

REFRESH_FLOW

Validate Refresh Token

↓

Verify Session

↓

Generate New JWT

↓

Rotate Refresh Token

↓

Audit

---

SESSION

Fields

session_id

user_id

workspace_id

device

browser

ip

created_at

expires_at

last_activity

revoked

---

SESSION_LIMITS

Maximum Active Sessions

5

---

Idle Timeout

30 Minutes

---

Absolute Timeout

30 Days

---

LOGOUT

Current Session

All Sessions

Forced Logout

---

FAILED_LOGIN

Attempt Counter

↓

Five Failures

↓

Temporary Lock

↓

Email Notification

↓

Audit

---

ACCOUNT_LOCK

Duration

15 Minutes

---

Reset After Successful Login

---

ROLE_LOADING

Load User

↓

Load Workspace

↓

Load Roles

↓

Load Permissions

↓

Generate Claims

↓

Issue JWT

---

AUTHORIZATION

RBAC

Workspace Isolation

Permission Based

Least Privilege

---

PUBLIC_ENDPOINTS

Register

Login

Verify Email

Forgot Password

Reset Password

Health

Landing

---

PROTECTED_ENDPOINTS

Dashboard

Reports

Billing

Admin

Settings

API

---

TOKEN_TRANSPORT (authoritative — resolves prior conflict with
implementation/00_FOUNDATION.md's "CSRF Disabled For JWT")

Access Token

Returned in response body on login/refresh. Client sends it via
`Authorization: Bearer <token>` header on every request. Never
stored in a cookie. Because it is never cookie-transported, it
carries no CSRF surface — implementation/00_FOUNDATION.md's
"CSRF Disabled For JWT" is correct for the access token specifically.

Refresh Token

Returned in response body, but the web frontend must store it in
an httpOnly, Secure, SameSite=Strict cookie scoped to path
`/api/v1/auth/refresh` only (mobile/native clients may store it in
secure device storage instead — no cookie applies there). SameSite=Strict
means the browser never attaches this cookie to a cross-site
request, which closes the CSRF surface without needing a separate
CSRF token — do not additionally implement double-submit CSRF
tokens for this endpoint, that would be redundant.

Validation

Reject any implementation that stores the access token in a cookie.

Reject any implementation that sends the refresh token cookie with
SameSite=Lax or SameSite=None.

---

SECURITY_RULES

HTTPS Only

Rate Limited

Input Validation

Output Encoding

Password Hashing

JWT Verification

---

RATE_LIMITS

Login

10/minute

---

Register

5/hour

---

Forgot Password

5/hour

---

Verify Email

10/hour

---

Refresh Token

60/hour

---

EVENTS

USER_REGISTERED

EMAIL_VERIFIED

LOGIN_SUCCESS

LOGIN_FAILED

PASSWORD_RESET_REQUESTED

PASSWORD_CHANGED

SESSION_CREATED

SESSION_REVOKED

ACCOUNT_LOCKED

ACCOUNT_UNLOCKED

GOOGLE_LOGIN_SUCCESS

---

DATABASE

users

sessions

roles

permissions

user_roles

password_reset_tokens

email_verification_tokens

oauth_accounts

audit_logs

---

API

POST

/api/v1/auth/register

POST

/api/v1/auth/login

POST

/api/v1/auth/google

POST

/api/v1/auth/logout

POST

/api/v1/auth/logout-all

POST

/api/v1/auth/refresh

POST

/api/v1/auth/forgot-password

POST

/api/v1/auth/reset-password

GET

/api/v1/auth/verify-email

GET

/api/v1/auth/me

---

ERRORS

INVALID_CREDENTIALS

EMAIL_NOT_VERIFIED

ACCOUNT_LOCKED

TOKEN_EXPIRED

TOKEN_INVALID

SESSION_EXPIRED

PERMISSION_DENIED

USER_NOT_FOUND

---

METRICS

Successful Logins

Failed Logins

Registrations

Password Resets

Email Verification Rate

Active Sessions

JWT Refresh Count

Locked Accounts

---

ACCEPTANCE

✓ Register

✓ Verify Email

✓ Login

✓ Logout

✓ Logout All

✓ Refresh Token

✓ Forgot Password

✓ Reset Password

✓ Google Login

✓ Session Revocation

✓ JWT Validation

✓ RBAC Validation

✓ Audit Created

---

CURSOR_RULES

Never store plaintext passwords.

Never expose refresh tokens.

Always hash passwords.

Always validate JWT.

Always rotate refresh tokens.

Always audit authentication events.

Always invalidate sessions after password reset.

Never trust frontend authorization.

Always validate permissions server-side.

Never expose user existence in authentication errors.

---

STATUS

COMPLETE

READY_FOR_CURSOR

TRUE