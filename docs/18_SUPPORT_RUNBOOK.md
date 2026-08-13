# 18_SUPPORT_RUNBOOK.md

---
document:
  id: DOC-018
  version: 1.0.0
  status: ACTIVE
  source_of_truth: true
---

module:

id:

MOD-SUPPORT

owner:

CUSTOMER_SUCCESS

---

goal:

Provide standardized operational procedures for customer support,
incident handling, workspace recovery, billing assistance,
and technical troubleshooting.

---

SUPPORT_LEVELS

L1

Customer Support

---

L2

Technical Support

---

L3

Engineering

---

L4

Platform Owner

---

SUPPORT_CHANNELS

Email

In-App Chat

Support Portal

Knowledge Base

Status Page

---

PRIORITIES

P1

Platform Down

Response

15 min

---

P2

Critical Business Impact

Response

30 min

---

P3

Normal Issue

Response

4 hours

---

P4

General Inquiry

Response

1 business day

---

CASE_STATES

OPEN

↓

ACKNOWLEDGED

↓

INVESTIGATING

↓

WAITING_CUSTOMER

↓

IN_PROGRESS

↓

RESOLVED

↓

CLOSED

---

CASE_TYPES

Authentication

Workspace

Billing

Subscription

Shopify

Razorpay

Reconciliation

Reports

Dashboard

Performance

Security

Feature Request

Bug Report

---

WORKFLOW

Customer Creates Ticket

↓

Assign Priority

↓

Assign Support Agent

↓

Collect Diagnostics

↓

Identify Root Cause

↓

Resolve

↓

Verify Customer

↓

Close Ticket

↓

Customer Feedback

---

STANDARD_DIAGNOSTICS

Workspace ID

User ID

Request ID

Correlation ID

Browser

Operating System

Timestamp

API Version

Error Code

Log Reference

---

PLAYBOOK

LOGIN_FAILURE

↓

Verify Account

↓

Verify Email

↓

Verify MFA

↓

Check Session

↓

Reset Password

↓

Escalate If Needed

---

PLAYBOOK

SHOPIFY_CONNECTION

↓

Verify OAuth

↓

Verify Token

↓

Verify Shop Domain

↓

Reconnect

↓

Retry Sync

↓

Escalate

---

PLAYBOOK

RAZORPAY_CONNECTION

↓

Verify API Keys

↓

Verify OAuth

↓

Retry Authentication

↓

Reconnect

↓

Run Validation

---

PLAYBOOK

SYNC_FAILURE

↓

Identify Failed Job

↓

Read Logs

↓

Retry Job

↓

Verify Import

↓

Resume Queue

---

PLAYBOOK

RECON_FAILURE

↓

Check Import

↓

Check Payments

↓

Check Orders

↓

Restart Engine

↓

Verify Results

---

PLAYBOOK

SUBSCRIPTION_FAILURE

↓

Verify Payment

↓

Verify Razorpay

↓

Retry Invoice

↓

Restore Subscription

↓

Notify Customer

---

PLAYBOOK

WORKSPACE_LOCKED

↓

Verify Status

↓

Verify Suspension

↓

Review Audit

↓

Unlock Workspace

↓

Verify Login

---

PLAYBOOK

DATA_RECOVERY

↓

Identify Backup

↓

Verify Permission

↓

Restore Backup

↓

Run Validation

↓

Customer Confirmation

---

ESCALATION_RULES

P1

Immediate Engineering

Immediate Platform Owner

---

P2

Engineering Within 30 Minutes

---

P3

Technical Support

---

P4

Customer Success

---

SECURITY_CASES

Compromised Account

Token Leak

Suspicious Login

Permission Abuse

API Abuse

Data Exposure

Unauthorized Access

---

SECURITY_RESPONSE

Lock Sessions

↓

Revoke Tokens

↓

Rotate Secrets

↓

Audit Review

↓

Notify Security

↓

Resolve

---

BILLING_OPERATIONS

Refund

Retry Payment

Invoice Generation

Subscription Upgrade

Subscription Downgrade

Cancel Subscription

Trial Extension

Coupon Verification

---

CUSTOMER_OPERATIONS

Reset Password

Reset MFA

Unlock Workspace

Reconnect Shopify

Reconnect Razorpay

Restart Sync

Restart Reconciliation

Export Reports

Generate Audit Export

---

SUPPORT_API

GET

/admin/support/cases

POST

/admin/support/cases

PATCH

/admin/support/cases/{id}

GET

/admin/support/diagnostics

POST

/admin/support/escalate

---

CASE_FIELDS

case_id

workspace_id

customer_id

priority

status

category

owner

created_at

updated_at

resolved_at

---

METRICS

tickets_open

tickets_closed

average_response_time

average_resolution_time

customer_satisfaction

first_response_time

reopened_cases

engineering_escalations

---

SLA

P1

15 Minutes

---

P2

30 Minutes

---

P3

4 Hours

---

P4

1 Business Day

---

KNOWLEDGE_BASE

Authentication

Billing

Shopify

Razorpay

Reports

Dashboard

Reconciliation

Workspace

API

Security

---

EVENTS

CASE_CREATED

CASE_ASSIGNED

CASE_ESCALATED

CASE_RESOLVED

CASE_CLOSED

CUSTOMER_REPLIED

ENGINEERING_ASSIGNED

---

AUDIT

Every support action logged

Every escalation logged

Every workspace change logged

Every billing action logged

Every recovery logged

---

CURSOR_RULES

Never modify customer data without audit.

Never restore data without authorization.

Never bypass RBAC.

Never expose secrets.

Every support action creates an audit event.

Every escalation preserves case history.

Every case is traceable using Request ID and Correlation ID.

---

ACCEPTANCE

✓ Ticket Created

✓ SLA Assigned

✓ Correct Routing

✓ Escalation Works

✓ Diagnostics Captured

✓ Customer Notified

✓ Audit Generated

✓ Case Closed Successfully

---

STATUS

COMPLETE

READY_FOR_CURSOR

TRUE