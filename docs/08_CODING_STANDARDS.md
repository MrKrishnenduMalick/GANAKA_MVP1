# 08_CODING_STANDARDS.md

# Ganaka Coding Standards

Version: 1.0.0

Status: Approved

---

# PURPOSE

This document defines the coding standards for Ganaka.

It specifies how production code must be written, organized, reviewed, and maintained.

These standards apply to every module in the repository.

---

# RULE CODE-001

Requirement

Every class must have a single responsibility.

Validation

Reject classes with multiple unrelated responsibilities.

---

# RULE CODE-002

Requirement

Business logic belongs only inside Service classes.

Allowed

✓ Validation

✓ Calculations

✓ Business Rules

✓ Transactions

Forbidden

✗ Controller

✗ Repository

✗ Entity

Validation

Reject business logic outside Services.

---

# RULE CODE-003

Requirement

Controllers must

• Receive requests

• Validate DTOs

• Call Services

• Return Responses

Forbidden

• Business Logic

• SQL

• Calculations

• Entity Manipulation

Validation

Reject fat controllers.

---

# RULE CODE-004

Requirement

Repositories only access the database.

Forbidden

Business Logic

Calculations

HTTP Calls

Validation

Reject repositories containing business rules.

---

# RULE CODE-005

Requirement

Entities represent persistent data only.

Forbidden

Business Logic

HTTP Logic

Validation

Reject smart entities.

---

# RULE CODE-006

Requirement

Every API must use DTOs.

Forbidden

Returning Entity objects.

Validation

Reject Entity exposure.

---

# RULE CODE-007

Requirement

Every DTO must be immutable.

Allowed

Constructor

Builder

Record

Forbidden

Public mutable fields.

Validation

Reject mutable DTOs.

---

# RULE CODE-008

Requirement

Dependency Injection is mandatory.

Forbidden

new Service()

new Repository()

Validation

Reject manual dependency creation.

---

# RULE CODE-009

Requirement

Methods should perform one logical operation.

Recommended Maximum

40 Lines

Validation

Review oversized methods.

---

# RULE CODE-010

Requirement

Class names must describe responsibility.

Examples

PaymentService

SettlementRepository

RefundController

Forbidden

Manager

Helper

Util

Stuff

Validation

Reject ambiguous names.

---

# RULE CODE-011

Requirement

Method names must describe behavior.

Examples

createWorkspace()

calculateSettlement()

findPayment()

Forbidden

doWork()

processData()

temp()

Validation

Reject unclear method names.

---

# RULE CODE-012

Requirement

Variables must use meaningful names.

Allowed

paymentAmount

workspaceId

orderStatus

Forbidden

x

abc

data

value

Validation

Reject unclear identifiers.

---

# RULE CODE-013

Requirement

Constants must replace magic values.

Forbidden

Hardcoded business constants.

Validation

Reject unexplained literals.

---

# RULE CODE-014

Requirement

Exceptions must be handled centrally.

Forbidden

Repeated try-catch blocks.

Validation

Reject duplicated exception handling.

---

# RULE CODE-015

Requirement

Logging must use structured logging.

Log

✓ Request ID

✓ Workspace ID

✓ User ID

✓ Action

Never Log

✗ Password

✗ JWT

✗ API Keys

✗ Secrets

Validation

Reject unsafe logs.

---

# RULE CODE-016

Requirement

Validation must occur before business logic.

Validation Includes

• Required Fields

• Format

• Range

• Business Constraints

Validation

Reject invalid input immediately.

---

# RULE CODE-017

Requirement

Transactions belong only in Services.

Forbidden

Transactional Controllers

Transactional Repositories

Validation

Reject incorrect transaction placement.

---

# RULE CODE-018

Requirement

Code duplication must be eliminated.

Preferred

Shared Services

Reusable Components

Forbidden

Copy-Paste Implementation

Validation

Reject duplicated logic.

---

# RULE CODE-019

Requirement

Every public method must have a clear contract.

Contract Includes

Inputs

Outputs

Exceptions

Side Effects

Validation

Reject undocumented public APIs.

---

# RULE CODE-020

Requirement

Every implementation must be testable.

Forbidden

Hidden dependencies

Static state

Hardcoded configuration

Validation

Reject code that cannot be unit tested.

---

# CODE REVIEW CHECKLIST

Before approving code verify

✓ Single Responsibility

✓ Business Logic in Services

✓ Thin Controllers

✓ Clean Repositories

✓ DTOs Used

✓ Dependency Injection

✓ Meaningful Names

✓ Validation Added

✓ Logging Added

✓ Tests Possible

---

# REFERENCES

Architecture

docs/03_ARCHITECTURE.md

API

docs/05_API_SPECIFICATION.md

Security

docs/06_SECURITY_REQUIREMENTS.md

Testing

docs/10_TESTING_STRATEGY.md

Implementation

implementation/

---

END OF DOCUMENT