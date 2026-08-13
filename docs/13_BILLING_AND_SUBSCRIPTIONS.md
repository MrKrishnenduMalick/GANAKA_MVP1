# 13_BILLING_AND_SUBSCRIPTIONS.md

# Ganaka Billing & Subscription Specification

Version: 1.0.0

Status: Approved

Owner: Billing Module

---

# PURPOSE

This document defines every billing rule used by Ganaka.

It specifies

- Plans
- Subscription lifecycle
- Billing state machine
- Invoice generation
- Payment lifecycle
- Upgrade policy
- Downgrade policy
- Cancellation
- Trial rules

Implementation details belong inside implementation/.

---

# BILLING MODEL

Business Model

Subscription SaaS

Billing Frequency

Monthly

Yearly

Currency

INR

Billing Provider

Configurable

---

# PLANS

FREE

Purpose

Evaluation

Limits

Workspace

1

Users

1

Store Connections

1

Reconciliation

Limited

Support

Community

---

PRO

Purpose

Growing Businesses

Limits

Unlimited Workspaces

Unlimited Users

Unlimited Stores

Advanced Reports

Alerts

Priority Support

---

ENTERPRISE

Purpose

Large Organizations

Limits

Unlimited Everything

Dedicated Support

Custom Integrations

SLA

Audit Features

---

# SUBSCRIPTION STATES

TRIAL

ACTIVE

PAST_DUE

GRACE_PERIOD

SUSPENDED

CANCELLED

EXPIRED

---

# RULE BILL-001

Purpose

Start Trial

Current State

NONE

Trigger

Workspace Created

Preconditions

No active subscription

Actions

Create Trial

Set Trial Expiry

Generate Audit Event

Next State

TRIAL

Failure

Reject duplicate trial.

Validation

One trial per workspace.

---

# RULE BILL-002

Purpose

Activate Subscription

Current State

TRIAL

Trigger

Successful Payment

Preconditions

Trial Valid

Actions

Create Invoice

Record Payment

Activate Subscription

Generate Audit Log

Next State

ACTIVE

Failure

Remain TRIAL

Validation

Subscription activates only after successful payment.

---

# RULE BILL-003

Purpose

Renew Subscription

Current State

ACTIVE

Trigger

Renewal Payment

Actions

Generate Invoice

Extend Expiry

Audit Event

Next State

ACTIVE

Failure

Move to PAST_DUE

Validation

Renewal must extend subscription period.

---

# RULE BILL-004

Purpose

Handle Failed Payment

Current State

ACTIVE

Trigger

Payment Failed

Actions

Retry Payment

Notify Customer

Create Audit Event

Next State

PAST_DUE

Validation

Never suspend immediately.

---

# RULE BILL-005

Purpose

Enter Grace Period

Current State

PAST_DUE

Trigger

Retry Limit Reached

Actions

Enable Grace Period

Notify Workspace Owner

Next State

GRACE_PERIOD

Validation

Grace period duration configurable.

---

# RULE BILL-006

Purpose

Suspend Subscription

Current State

GRACE_PERIOD

Trigger

Grace Expired

Actions

Disable Premium Features

Keep Data

Audit Event

Next State

SUSPENDED

Validation

Never delete customer data.

---

# RULE BILL-007

Purpose

Restore Subscription

Current State

SUSPENDED

Trigger

Successful Payment

Actions

Restore Features

Generate Invoice

Audit Event

Next State

ACTIVE

Validation

No data restoration required.

---

# RULE BILL-008

Purpose

Cancel Subscription

Current State

ACTIVE

Trigger

Customer Cancellation

Actions

Mark Cancelled

Keep Access Until Expiry

Generate Audit

Next State

CANCELLED

Validation

Cancellation never refunds automatically.

---

# RULE BILL-009

Purpose

Expire Subscription

Current State

CANCELLED

Trigger

Subscription Expiry

Actions

Disable Premium Features

Archive Billing

Generate Audit

Next State

EXPIRED

Validation

Historical invoices remain accessible.

---

# RULE BILL-010

Purpose

Upgrade Plan

Current State

ACTIVE

Trigger

Upgrade Request

Actions

Calculate Proration

Generate Invoice

Activate New Plan

Audit Event

Next State

ACTIVE

Validation

Upgrade effective immediately.

---

# RULE BILL-011

Purpose

Downgrade Plan

Current State

ACTIVE

Trigger

Downgrade Request

Actions

Schedule Downgrade

Notify Customer

Audit Event

Next State

ACTIVE

Validation

Downgrade effective next billing cycle.

---

# RULE BILL-012

Purpose

Invoice Generation

Trigger

Successful Charge

Invoice Must Include

Invoice Number

Workspace

Plan

Amount

Tax

Currency

Issue Date

Validation

Every successful payment creates exactly one invoice.

---

# RULE BILL-013

Purpose

Refund

Trigger

Approved Refund

Actions

Generate Credit Note

Record Refund

Audit Event

Validation

Refund never deletes original invoice.

---

# RULE BILL-014

Purpose

Plan Change

Validation

Plan changes never modify historical invoices.

---

# RULE BILL-015

Purpose

Billing History

Requirement

Billing history is immutable.

Validation

Never edit historical invoices.

---

# RULE BILL-016

Purpose

Audit

Every billing action generates

Workspace

User

Timestamp

Action

Invoice

Subscription

Validation

Reject unaudited billing actions.

---

# RULE BILL-017

Purpose

Taxes

Requirement

Taxes calculated before invoice generation.

Validation

Invoice total equals

Subtotal + Tax

---

# RULE BILL-018

Purpose

Notifications

Generate notifications for

Trial Ending

Payment Failed

Invoice Generated

Subscription Activated

Subscription Suspended

Validation

Duplicate notifications prohibited.

---

# RULE BILL-019

Purpose

Data Retention

Requirement

Billing data retained permanently.

Validation

Never hard delete invoices.

---

# RULE BILL-020

Purpose

Billing Integrity

Requirement

Every subscription has

One Current State

One Active Plan

Complete Billing History

Validation

Reject inconsistent billing state.

---

# BILLING STATE MACHINE

NONE

↓

TRIAL

↓

ACTIVE

↓

PAST_DUE

↓

GRACE_PERIOD

↓

SUSPENDED

↓

ACTIVE

or

↓

CANCELLED

↓

EXPIRED

---

# BILLING REVIEW CHECKLIST

✓ State transition valid

✓ Invoice generated

✓ Audit logged

✓ Notifications sent

✓ Payment recorded

✓ History preserved

✓ No duplicate invoices

✓ Plan updated

✓ Billing state consistent

---

# REFERENCES

Product Requirements

docs/02_PRODUCT_REQUIREMENTS.md

Business Rules

docs/07_BUSINESS_RULES.md

Implementation

implementation/

---

END OF DOCUMENT