# 03_ARCHITECTURE.md

# Ganaka System Architecture

Version: 1.0.0

Status: Approved

---

# PURPOSE

This document defines the system architecture of Ganaka.

It specifies how the application is organized, how modules interact, and the approved technology stack.

It does not contain business rules, database schema, API specifications, or coding standards.

---

# ARCHITECTURE PRINCIPLES

Ganaka follows these architectural principles.

- Layered Architecture
- Modular Design
- Domain Separation
- Single Responsibility
- Dependency Injection
- Stateless Services
- Event-Driven where appropriate
- API First
- Security by Design

---

# SYSTEM OVERVIEW

Ganaka consists of four major layers.

```
                Client Layer
        ┌─────────────────────────┐
        │ Next.js Frontend        │
        └────────────┬────────────┘
                     │ HTTPS
        ┌────────────▼────────────┐
        │ Spring Boot REST API    │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │ Business Services       │
        │ Reconciliation Engine   │
        │ Finance Engine          │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │ PostgreSQL Database     │
        └─────────────────────────┘
```

---

# TECHNOLOGY STACK

Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS

Backend

- Java
- Spring Boot
- Spring Security
- Spring Data JPA
- Flyway

Database

- PostgreSQL

Authentication

- JWT
- Refresh Tokens

Storage

- Cloud Storage (configurable)

Caching

- Redis

Queue (Future)

- RabbitMQ / Kafka (optional)

Deployment

- Docker
- GitHub Actions
- Cloud Platform

---

# MODULE STRUCTURE

The backend is divided into functional modules.

- Authentication
- Workspace
- Users
- Shopify
- Razorpay
- Finance
- Reconciliation
- Reports
- Notifications
- Dashboard
- Platform

Each module owns its own business logic.

---

# LAYERED ARCHITECTURE

Each module follows the same layers.

```
Controller

↓

Service

↓

Repository

↓

Database
```

Supporting components.

- DTO
- Entity
- Mapper
- Validator
- Exception Handler
- Configuration

Business logic belongs only inside the Service layer.

---

# DEPENDENCY RULES

Allowed dependencies

Controller

→ Service

Service

→ Repository

Repository

→ Database

Forbidden

Controller → Repository

Controller → Entity

Repository → Controller

Service → Controller

Cross-module database access

---

# MODULE COMMUNICATION

Modules communicate only through

- Service interfaces
- Events
- Well-defined APIs

Never access another module's internal implementation directly.

---

# REQUEST FLOW

```
Client

↓

REST Controller

↓

Validation

↓

Service

↓

Repository

↓

Database

↓

Service

↓

DTO

↓

HTTP Response
```

---

# ERROR FLOW

```
Exception

↓

Global Exception Handler

↓

Standard Error Response

↓

Client
```

---

# AUTHENTICATION FLOW

```
Login

↓

Authentication

↓

JWT Issued

↓

Authenticated Requests

↓

Authorization

↓

Business Logic
```

---

# MULTI-TENANCY

Every request belongs to exactly one workspace.

Every database query must respect workspace boundaries.

No tenant may access another tenant's data.

---

# CONFIGURATION

Configuration is externalized.

Examples

- Environment Variables
- application.yml
- Secrets Manager

Never hardcode credentials.

---

# SCALABILITY

The architecture must support

- Horizontal scaling
- Stateless backend services
- Independent module evolution
- Future microservice migration

without changing current module boundaries.

---

# OBSERVABILITY

The architecture supports

- Structured Logging
- Metrics
- Health Checks
- Audit Logs
- Error Tracking

Implementation details belong in

docs/16_MONITORING_AND_OBSERVABILITY.md

---

# SECURITY

Security implementation is defined in

docs/06_SECURITY_REQUIREMENTS.md

---

# DATABASE

Database design is defined in

docs/04_DATABASE_SPECIFICATION.md

---

# API

API contracts are defined in

docs/05_API_SPECIFICATION.md

---

# IMPLEMENTATION

Each functional module is implemented according to its corresponding document in

implementation/

---

# ARCHITECTURE CONSTRAINTS

Never

- Skip layers
- Access repositories from controllers
- Share entities across modules
- Duplicate business logic
- Introduce circular dependencies
- Break module boundaries

---

# ARCHITECTURE REVIEW CHECKLIST

Before completing any feature verify

✓ Layered architecture is preserved

✓ Module boundaries are respected

✓ Dependencies are valid

✓ No circular dependencies

✓ Security remains intact

✓ Multi-tenancy is enforced

✓ Configuration remains external

---

END OF DOCUMENT