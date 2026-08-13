# 11_ENVIRONMENT_SPEC.md

# Ganaka Environment Specification

Version: 1.0.0

Status: Approved

---

# PURPOSE

This document defines all environment configurations used by Ganaka.

It specifies runtime environments, configuration management, required environment variables, secrets handling, and deployment profiles.

Business logic must never depend on environment-specific behavior.

---

# ENVIRONMENTS

Supported Environments

- Local Development
- Development
- Testing
- Staging
- Production

Validation

Reject undefined environments.

---

# RULE ENV-001

Requirement

Every environment must have its own configuration profile.

Profiles

local

dev

test

staging

prod

Validation

Reject shared configuration files.

---

# RULE ENV-002

Requirement

Environment variables are the only source for runtime configuration.

Allowed

Database URL

JWT Secret

Redis URL

SMTP Configuration

API Keys

Forbidden

Hardcoded configuration values.

Validation

Reject embedded configuration.

---

# RULE ENV-003

Requirement

Every required environment variable must be documented.

Validation

Reject undocumented variables.

---

# RULE ENV-004

Requirement

Secrets must never be committed to Git.

Examples

JWT_SECRET

DATABASE_PASSWORD

SHOPIFY_CLIENT_SECRET

RAZORPAY_SECRET

SMTP_PASSWORD

Validation

Reject committed secrets.

---

# RULE ENV-005

Requirement

Every environment must have its own database.

Forbidden

Production database used for testing.

Validation

Reject shared databases.

---

# RULE ENV-006

Requirement

Every environment must have isolated storage.

Examples

Uploads

Logs

Backups

Exports

Validation

Reject shared storage.

---

# RULE ENV-007

Requirement

Production must use HTTPS only.

Forbidden

HTTP

Validation

Reject insecure production deployment.

---

# RULE ENV-008

Requirement

Debug mode must never be enabled in Production.

Validation

Reject debug configuration.

---

# RULE ENV-009

Requirement

Logging level

Local

DEBUG

Development

INFO

Testing

INFO

Staging

WARN

Production

ERROR

Validation

Reject incorrect log levels.

---

# RULE ENV-010

Requirement

Every environment must expose Health Checks.

Minimum Endpoints

/health

/ready

/live

Validation

Reject missing health endpoints.

---

# RULE ENV-011

Requirement

Application configuration must be externalized.

Examples

application-local.yml

application-dev.yml

application-test.yml

application-staging.yml

application-prod.yml

Validation

Reject environment-specific code.

---

# RULE ENV-012

Requirement

Feature flags must be environment configurable.

Forbidden

Hardcoded feature toggles.

Validation

Reject fixed feature states.

---

# RULE ENV-013

Requirement

Every external integration must support sandbox configuration.

Examples

Shopify

Razorpay

SMTP

Validation

Reject production credentials in non-production environments.

---

# RULE ENV-014

Requirement

Environment variables must have validation.

Examples

Required

Format

Allowed Values

Validation

Application startup fails on invalid configuration.

---

# RULE ENV-015

Requirement

Missing required configuration prevents application startup.

Validation

Fail fast.

---

# RULE ENV-016

Requirement

Container configuration must remain environment-independent.

Validation

Reject environment-specific Docker images.

---

# RULE ENV-017

Requirement

Timezone

UTC

Validation

Reject local timezone configuration.

---

# RULE ENV-018

Requirement

Character Encoding

UTF-8

Validation

Reject inconsistent encoding.

---

# RULE ENV-019

Requirement

Every environment must support automated deployment.

Validation

Reject manual-only deployments.

---

# RULE ENV-020

Requirement

Environment configuration changes require documentation updates.

Validation

Reject undocumented configuration changes.

---

# REQUIRED ENVIRONMENT VARIABLES

Database

DATABASE_URL

DATABASE_USERNAME

DATABASE_PASSWORD

Authentication

JWT_SECRET

JWT_EXPIRATION

JWT_REFRESH_EXPIRATION

Redis

REDIS_HOST

REDIS_PORT

Email

SMTP_HOST

SMTP_PORT

SMTP_USERNAME

SMTP_PASSWORD

Shopify

SHOPIFY_CLIENT_ID

SHOPIFY_CLIENT_SECRET

Razorpay

RAZORPAY_KEY_ID

RAZORPAY_KEY_SECRET

Application

APP_ENV

APP_NAME

APP_URL

LOG_LEVEL

---

# ENVIRONMENT REVIEW CHECKLIST

Before deployment verify

✓ Correct profile selected

✓ Secrets configured

✓ Database configured

✓ Redis configured

✓ External integrations configured

✓ HTTPS enabled

✓ Health checks available

✓ Logging configured

✓ Required variables present

✓ No hardcoded values

---

# REFERENCES

Architecture

docs/03_ARCHITECTURE.md

Security

docs/06_SECURITY_REQUIREMENTS.md

Release Process

docs/12_RELEASE_PROCESS.md

Implementation

implementation/

---

END OF DOCUMENT