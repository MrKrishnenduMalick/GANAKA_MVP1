# 15_CUSTOMER_ONBOARDING.md

---
document:
  id: DOC-015
  name: CUSTOMER_ONBOARDING
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

## MODULE

module:
  id: MOD-ONBOARDING
  owner: PLATFORM
  type: CORE
  depends_on:
    - DOC-003
    - DOC-004
    - DOC-005
    - DOC-006
    - DOC-007
    - DOC-013

---

## GOAL

goal:

Create a production-ready onboarding system that allows a customer to:

- Register
- Verify email
- Create workspace
- Connect Shopify
- Connect Razorpay
- Import historical data
- Execute first reconciliation
- Activate workspace

---

## ENTITY

entity:

ONBOARDING

primary_key:

onboarding_id

fields:

- onboarding_id
- workspace_id
- owner_user_id
- state
- trial_start
- trial_end
- created_at
- updated_at

---

## STATE MACHINE

state_machine:

id:

SM-001

entity:

ONBOARDING

initial:

CREATED

terminal:

ACTIVE

states:

CREATED

↓

EMAIL_VERIFIED

↓

WORKSPACE_CREATED

↓

PROFILE_COMPLETED

↓

SHOPIFY_CONNECTED

↓

SHOPIFY_ONLY_ACTIVE (branch — see below)

↓ (optional, merchant-initiated)

RAZORPAY_CONNECTED

↓

INITIAL_SYNC_RUNNING

↓

INITIAL_SYNC_COMPLETED

↓

FIRST_RECON_COMPLETED

↓

ACTIVE

BRANCH: SHOPIFY_ONLY_ACTIVE

A workspace reaches SHOPIFY_ONLY_ACTIVE immediately after
SHOPIFY_CONNECTED + its own Shopify-only initial sync completes,
WITHOUT requiring Razorpay. This state unlocks the Dashboard showing
Shopify order/revenue data (no reconciliation yet, since
reconciliation requires both sources per BR-005). Razorpay connection
is then presented as the clear next step to unlock reconciliation,
not a mandatory onboarding gate.

Reason

Forcing Razorpay connection before any value is shown blocks
merchants who don't yet have (or don't use) a Razorpay account —
including COD-only or evaluation-stage merchants — from ever seeing
the product work. See implementation/07_RECONCILIATION_ENGINE.md
DISCREPANCY DECISION TABLE Step 0 for how non-Razorpay orders are
handled once Razorpay IS eventually connected.

forbidden:

ACTIVE → CREATED

SHOPIFY_CONNECTED → EMAIL_VERIFIED

INITIAL_SYNC_COMPLETED → CREATED

SHOPIFY_ONLY_ACTIVE → CREATED

---

## BUSINESS RULES

rule:

id: ONBOARDING-001

email must be unique

---

rule:

id: ONBOARDING-002

workspace slug unique

---

rule:

id: ONBOARDING-003

workspace owner required

---

rule:

id: ONBOARDING-004

email verification required before OAuth

---

rule:

id: ONBOARDING-005

Shopify required before reconciliation

---

rule:

id: ONBOARDING-006

Razorpay required before reconciliation

---

rule:

id: ONBOARDING-007

trial starts after workspace creation

---

rule:

id: ONBOARDING-008

trial cannot exceed configured duration

---

## WORKFLOW

workflow:

id:

WF-REGISTER

trigger:

SIGN_UP

actor:

PUBLIC

transaction:

validate_email

validate_password

create_user

create_workspace

create_owner_role

create_permissions

create_trial

create_onboarding

send_verification_email

emit:

EVENT_USER_REGISTERED

rollback:

delete_workspace

delete_user

---

workflow:

id:

WF-VERIFY-EMAIL

trigger:

EMAIL_VERIFICATION

transaction:

validate_token

mark_verified

advance_state

audit

emit:

EVENT_EMAIL_VERIFIED

---

workflow:

id:

WF-COMPLETE-PROFILE

transaction:

save_company

save_gst

save_timezone

save_currency

advance_state

audit

---

workflow:

id:

WF-CONNECT-SHOPIFY

trigger:

SHOPIFY_OAUTH

transaction:

validate_shop

exchange_token

encrypt_token

store_credentials

test_connection

advance_state

emit:

EVENT_SHOPIFY_CONNECTED

rollback:

delete_credentials

---

workflow:

id:

WF-CONNECT-RAZORPAY

trigger:

RAZORPAY_OAUTH

transaction:

exchange_token

encrypt

validate

store

advance_state

emit:

EVENT_RAZORPAY_CONNECTED

---

workflow:

id:

WF-INITIAL-SYNC

transaction:

fetch_orders

fetch_refunds

fetch_payments

fetch_settlements

persist

audit

advance_state

emit:

EVENT_INITIAL_SYNC_COMPLETE

---

workflow:

id:

WF-FIRST-RECON

transaction:

run_reconciliation

calculate_matches

calculate_missing

calculate_disputes

generate_dashboard

advance_state

emit:

EVENT_FIRST_RECON_DONE

---

## EVENTS

EVENT_USER_REGISTERED

producer:

AUTH

consumers:

EMAIL

AUDIT

ONBOARDING

---

EVENT_EMAIL_VERIFIED

producer:

AUTH

consumers:

ONBOARDING

AUDIT

---

EVENT_SHOPIFY_CONNECTED

producer:

SHOPIFY

consumers:

SYNC

AUDIT

---

EVENT_RAZORPAY_CONNECTED

producer:

RAZORPAY

consumers:

SYNC

AUDIT

---

EVENT_INITIAL_SYNC_COMPLETE

producer:

SYNC

consumers:

RECON

AUDIT

---

EVENT_FIRST_RECON_DONE

producer:

RECON

consumers:

DASHBOARD

REPORTS

NOTIFICATION

---

## API CONTRACTS

POST

/api/auth/register

POST

/api/auth/verify-email

POST

/api/onboarding/profile

GET

/api/shopify/oauth

GET

/api/razorpay/oauth

POST

/api/onboarding/start-sync

POST

/api/onboarding/run-first-reconciliation

GET

/api/onboarding/status

GET

/api/onboarding/progress

---

## DATABASE IMPACT

tables:

users

workspace

workspace_member

role

permission

user_role

shopify_connection

razorpay_connection

sync_job

reconciliation_job

trial

audit_log

onboarding

---

## FAILURE RECOVERY

retry:

shopify_oauth

3

retry:

razorpay_oauth

3

retry:

initial_sync

5

retry:

reconciliation

5

dead_letter:

enabled

---

## PERFORMANCE

workspace_creation:

<500ms

oauth:

<2s

initial_sync:

background

dashboard_ready:

<10s after sync

---

## ACCEPTANCE

✓ User registers

✓ Email verified

✓ Workspace created

✓ Trial activated

✓ Shopify connected

✓ Razorpay connected

✓ Initial sync completed

✓ First reconciliation completed

✓ Dashboard generated

✓ Customer active

---

status:

COMPLETE

ready_for_cursor:

true