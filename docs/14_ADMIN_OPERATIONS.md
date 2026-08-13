################################################################################
# FILE
################################################################################

file:
  id: DOC-014
  name: ADMIN_OPERATIONS
  version: 1.0.0
  status: ACTIVE
  priority: CRITICAL
  owner: PLATFORM
  source_of_truth: true

################################################################################
# PURPOSE
################################################################################

purpose:

  objective: >
    Defines every privileged platform operation available inside Ganaka.

  scope:

    includes:

      - Admin Authentication

      - RBAC

      - Workspace Operations

      - User Operations

      - Subscription Operations

      - Security Operations

      - Incident Operations

      - Feature Flags

      - Audit

      - Internal Admin APIs

    excludes:

      - Customer Dashboard

      - Merchant Dashboard

      - Public APIs

################################################################################
# DEPENDENCIES
################################################################################

dependencies:

  required:

    - DOC-003

    - DOC-004

    - DOC-005

    - DOC-006

    - DOC-007

    - DOC-009

    - DOC-013

################################################################################
# DOMAIN
################################################################################

domain:

  entities:

    - Admin

    - Role

    - Permission

    - Workspace

    - User

    - Session

    - Incident

    - AuditLog

    - FeatureFlag

    - Subscription

################################################################################
# ADMIN TYPES
################################################################################

catalog:

  admin_types:

    PLATFORM_OWNER:

      immutable: true

      description: Full platform ownership

    PLATFORM_ADMIN:

      immutable: false

      description: Platform administration

    SUPPORT_ADMIN:

      immutable: false

      description: Customer support

    SECURITY_ADMIN:

      immutable: false

      description: Security management

    FINANCE_ADMIN:

      immutable: false

      description: Billing management

    AUDITOR:

      immutable: true

      description: Read only auditing

################################################################################
# RBAC
################################################################################

permissions:

  workspace:

    - workspace.read

    - workspace.update

    - workspace.archive

    - workspace.restore

    - workspace.suspend

    - workspace.activate

    - workspace.transfer

    - workspace.delete

  user:

    - user.read

    - user.update

    - user.disable

    - user.enable

    - user.reset_password

    - user.reset_mfa

    - user.force_logout

  billing:

    - subscription.read

    - subscription.retry

    - subscription.cancel

    - subscription.refund

  security:

    - session.terminate

    - api_key.revoke

    - secret.rotate

    - ip.block

    - ip.unblock

  audit:

    - audit.read

    - audit.export

################################################################################
# ROLE MATRIX
################################################################################

role_matrix:

  PLATFORM_OWNER:

    permissions: "*"

  PLATFORM_ADMIN:

    permissions:

      - workspace.*

      - user.*

      - audit.read

      - subscription.read

  SUPPORT_ADMIN:

    permissions:

      - workspace.read

      - user.read

      - user.reset_password

      - user.reset_mfa (reserved — inactive until MFA ships; see
        implementation/01_AUTHENTICATION.md LOGIN_FLOW "MFA (Future)".
        Do not implement this permission's handler before MFA itself
        exists, and do not remove it from the matrix — it documents
        the intended V2 shape.)

      - user.force_logout

  FINANCE_ADMIN:

    permissions:

      - subscription.*

      - audit.read

  SECURITY_ADMIN:

    permissions:

      - session.*

      - api_key.*

      - secret.*

      - ip.*

  AUDITOR:

    permissions:

      - audit.read

      - audit.export

################################################################################
# RULES
################################################################################

rules:

  - id: ADMIN-001

    title: Authentication Required

    actor:

      - ALL

    condition:

      authenticated: true

    result:

      allow_access: true

    error:

      ADMIN-401

  - id: ADMIN-002

    title: MFA Required

    actor:

      - ALL

    condition:

      mfa_verified: true

    error:

      ADMIN-402

  - id: ADMIN-003

    title: Least Privilege

    description:

      Every administrator receives only the permissions required.

  - id: ADMIN-004

    title: Permission Validation

    description:

      Every request validates permission before business execution.

  - id: ADMIN-005

    title: Audit Mandatory

    description:

      Every successful and failed admin action generates an audit event.

  - id: ADMIN-006

    title: No Permission Escalation

    description:

      Administrator cannot assign permissions above own privilege.

  - id: ADMIN-007

    title: Workspace Isolation

    description:

      Admin operations must never leak tenant data.

################################################################################
# STATES
################################################################################

states:

  admin:

    ACTIVE:

      transitions:

        - SUSPENDED

        - REVOKED

    SUSPENDED:

      transitions:

        - ACTIVE

    REVOKED:

      transitions: []

################################################################################
# WORKFLOW
################################################################################

workflow:

  id: WORKFLOW-ADMIN-LOGIN

  trigger:

    ADMIN_LOGIN

  preconditions:

    - valid_credentials

    - active_account

    - mfa_verified

  transaction:

    - create_session

    - generate_jwt

    - register_device

    - create_audit

  rollback: []

  success:

    ADMIN_SESSION_CREATED

  failure:

    - ADMIN-401

    - ADMIN-402

################################################################################
# EVENTS
################################################################################

events:

  - id: EVENT-ADMIN-LOGIN

    producer:

      AUTH_SERVICE

    consumers:

      - AUDIT_SERVICE

      - SECURITY_SERVICE

    payload:

      - admin_id

      - ip

      - device

      - timestamp

  - id: EVENT-WORKSPACE-SUSPENDED

    producer:

      ADMIN_SERVICE

    consumers:

      - API_GATEWAY

      - JOB_SERVICE

      - AUDIT_SERVICE

################################################################################
# AUDIT
################################################################################

audit:

  mandatory: true

  immutable: true

  fields:

    - audit_id

    - actor

    - permission

    - workspace

    - target

    - previous_value

    - new_value

    - request_id

    - correlation_id

    - ip

    - device

    - timestamp

################################################################################
# REFERENCES
################################################################################

references:

  - DOC-003

  - DOC-004

  - DOC-005

  - DOC-006

  - DOC-007

  - DOC-013
################################################################################
# WORKSPACE OPERATIONS
################################################################################

workspaces:

  lifecycle:

    states:

      ACTIVE:

        allowed:

          - SUSPENDED

          - ARCHIVED

      SUSPENDED:

        allowed:

          - ACTIVE

          - ARCHIVED

      ARCHIVED:

        allowed:

          - ACTIVE

          - DELETED

      DELETED:

        terminal: true

################################################################################
# WORKFLOW
################################################################################

workflow:

  id: WORKSPACE-SUSPEND

  trigger:

    ADMIN_CLICK_SUSPEND

  actor:

    PLATFORM_OWNER

    PLATFORM_ADMIN

  permissions:

    - workspace.suspend

  preconditions:

    - workspace_exists

    - workspace_state == ACTIVE

    - admin_authenticated

    - admin_mfa_verified

  validation:

    - tenant_exists

    - no_running_migration

  transaction:

    - revoke_active_sessions

    - disable_login

    - disable_api_tokens

    - pause_webhooks

    - pause_cron_jobs

    - update_workspace_status

    - generate_audit_log

    - notify_workspace_owner

  rollback:

    - restore_previous_state

  emits:

    - EVENT-WORKSPACE-SUSPENDED

################################################################################

workflow:

  id: WORKSPACE-ACTIVATE

  trigger:

    ADMIN_CLICK_ACTIVATE

  permissions:

    - workspace.activate

  preconditions:

    - workspace_state == SUSPENDED

  transaction:

    - enable_login

    - enable_api

    - enable_webhooks

    - resume_jobs

    - create_audit

  emits:

    - EVENT-WORKSPACE-ACTIVATED

################################################################################

workflow:

  id: WORKSPACE-ARCHIVE

  trigger:

    ADMIN_CLICK_ARCHIVE

  permissions:

    - workspace.archive

  transaction:

    - readonly_mode

    - disable_write_api

    - preserve_data

    - create_audit

################################################################################

workflow:

  id: WORKSPACE-DELETE

  trigger:

    ADMIN_CLICK_DELETE

  permissions:

    - workspace.delete

  preconditions:

    - retention_complete

    - double_confirmation

    - owner_verified

  transaction:

    - enqueue_delete

    - archive_backup

    - delete_storage

    - delete_objects

    - create_audit

################################################################################
# USER OPERATIONS
################################################################################

users:

  lifecycle:

    ACTIVE:

      transitions:

        - DISABLED

        - LOCKED

    LOCKED:

      transitions:

        - ACTIVE

    DISABLED:

      transitions:

        - ACTIVE

################################################################################

workflow:

  id: USER-DISABLE

  permissions:

    - user.disable

  transaction:

    - revoke_tokens

    - terminate_sessions

    - disable_login

    - create_audit

    - notify_user

################################################################################

workflow:

  id: USER-ENABLE

  permissions:

    - user.enable

  transaction:

    - enable_login

    - issue_new_session

    - create_audit

################################################################################

workflow:

  id: USER-RESET-PASSWORD

  permissions:

    - user.reset_password

  transaction:

    - invalidate_password

    - generate_reset_link

    - expire_sessions

    - email_reset_link

    - audit

################################################################################

workflow:

  id: USER-RESET-MFA

  permissions:

    - user.reset_mfa

  transaction:

    - remove_existing_mfa

    - require_setup_next_login

    - revoke_sessions

    - audit

################################################################################

workflow:

  id: USER-FORCE-LOGOUT

  permissions:

    - user.force_logout

  transaction:

    - revoke_access_token

    - revoke_refresh_token

    - destroy_sessions

    - audit

################################################################################
# FEATURE FLAGS
################################################################################

feature_flags:

  schema:

    id:

    key:

    enabled:

    rollout:

    workspace_override:

    created_by:

    updated_by:

################################################################################

flag_states:

  OFF:

    transitions:

      - ON

      - ROLLOUT

  ROLLOUT:

    transitions:

      - ON

      - OFF

  ON:

    transitions:

      - OFF

      - EMERGENCY_OFF

  EMERGENCY_OFF:

    transitions:

      - OFF

################################################################################

workflow:

  id: FEATUREFLAG-UPDATE

  permissions:

    - featureflag.manage

  transaction:

    - validate_flag

    - update_configuration

    - clear_cache

    - propagate_cluster

    - audit

################################################################################
# INCIDENT MANAGEMENT
################################################################################

incident:

  severities:

    P1:

      response: 15m

      target: platform_down

    P2:

      response: 30m

    P3:

      response: 2h

    P4:

      response: next_release

################################################################################

incident_states:

  OPEN:

    transitions:

      - INVESTIGATING

  INVESTIGATING:

    transitions:

      - IDENTIFIED

      - RESOLVED

  IDENTIFIED:

    transitions:

      - FIXING

  FIXING:

    transitions:

      - MONITORING

  MONITORING:

    transitions:

      - RESOLVED

  RESOLVED:

    transitions:

      - POSTMORTEM

################################################################################

workflow:

  id: INCIDENT-CREATE

  permissions:

    - incident.manage

  transaction:

    - generate_incident

    - assign_owner

    - notify_team

    - create_timeline

################################################################################

workflow:

  id: INCIDENT-RESOLVE

  transaction:

    - mark_resolved

    - notify_subscribers

    - archive_logs

    - create_postmortem_task

################################################################################
# SECURITY OPERATIONS
################################################################################

workflow:

  id: BLOCK-IP

  permissions:

    - ip.block

  transaction:

    - update_firewall

    - invalidate_requests

    - create_audit

################################################################################

workflow:

  id: ROTATE-SECRETS

  permissions:

    - secret.rotate

  transaction:

    - generate_secret

    - encrypt

    - distribute

    - invalidate_previous

    - audit

################################################################################

workflow:

  id: REVOKE-API-KEY

  permissions:

    - api_key.revoke

  transaction:

    - disable_key

    - remove_cache

    - audit

################################################################################

workflow:

  id: TERMINATE-SESSIONS

  permissions:

    - session.terminate

  transaction:

    - destroy_all_sessions

    - revoke_refresh_tokens

    - revoke_access_tokens

    - audit

################################################################################
# EVENTS
################################################################################

events:

  EVENT-WORKSPACE-ACTIVATED:

    producer:

      ADMIN_SERVICE

    consumers:

      API_GATEWAY

      JOB_SERVICE

      AUDIT_SERVICE

  EVENT-USER-DISABLED:

    producer:

      ADMIN_SERVICE

    consumers:

      AUTH_SERVICE

      NOTIFICATION_SERVICE

      AUDIT_SERVICE

  EVENT-FEATUREFLAG-UPDATED:

    producer:

      ADMIN_SERVICE

    consumers:

      CACHE

      API_GATEWAY

      FRONTEND

  EVENT-INCIDENT-CREATED:

    producer:

      INCIDENT_SERVICE

    consumers:

      EMAIL

      SLACK

      AUDIT

      DASHBOARD
################################################################################
# INTERNAL ADMIN API CONTRACTS
################################################################################

admin_api:

  base_path: /api/v1/admin

  authentication:

    required: true

    jwt: ADMIN_ACCESS_TOKEN

    mfa: REQUIRED

  authorization:

    engine: RBAC

    validation_order:

      - authenticate

      - authorize

      - workspace_scope

      - rate_limit

      - execute

      - audit

################################################################################

endpoint:

  id: ADMIN-API-001

  method: GET

  path: /dashboard

  permission:

    - dashboard.read

  response:

    metrics:

      - total_users

      - active_workspaces

      - active_subscriptions

      - failed_payments

      - open_incidents

      - active_jobs

      - queue_depth

      - api_latency

################################################################################

endpoint:

  id: ADMIN-API-002

  method: GET

  path: /workspaces

  permission:

    - workspace.read

  pagination:

    cursor: true

    limit:

      default: 50

      maximum: 200

################################################################################

endpoint:

  id: ADMIN-API-003

  method: PATCH

  path: /workspaces/{workspaceId}/suspend

  permission:

    - workspace.suspend

  workflow:

    WORKSPACE-SUSPEND

################################################################################

endpoint:

  id: ADMIN-API-004

  method: PATCH

  path: /workspaces/{workspaceId}/activate

  permission:

    - workspace.activate

################################################################################

endpoint:

  id: ADMIN-API-005

  method: DELETE

  path: /workspaces/{workspaceId}

  permission:

    - workspace.delete

################################################################################

endpoint:

  id: ADMIN-API-006

  method: POST

  path: /users/{userId}/force-logout

  permission:

    - user.force_logout

################################################################################

endpoint:

  id: ADMIN-API-007

  method: POST

  path: /users/{userId}/reset-password

  permission:

    - user.reset_password

################################################################################

endpoint:

  id: ADMIN-API-008

  method: POST

  path: /users/{userId}/reset-mfa

  permission:

    - user.reset_mfa

################################################################################

endpoint:

  id: ADMIN-API-009

  method: PATCH

  path: /feature-flags/{flagId}

  permission:

    - featureflag.manage

################################################################################

endpoint:

  id: ADMIN-API-010

  method: POST

  path: /incidents

  permission:

    - incident.manage

################################################################################

endpoint:

  id: ADMIN-API-011

  method: PATCH

  path: /incidents/{incidentId}

  permission:

    - incident.manage

################################################################################

endpoint:

  id: ADMIN-API-012

  method: GET

  path: /audit

  permission:

    - audit.read

################################################################################

endpoint:

  id: ADMIN-API-013

  method: GET

  path: /audit/export

  permission:

    - audit.export

################################################################################
# DATABASE IMPACT
################################################################################

database:

  tables:

    admin_users:

      primary_key:

        admin_id

      indexes:

        - email

        - role

        - status

    admin_roles:

      primary_key:

        role_id

    admin_permissions:

      primary_key:

        permission_id

    admin_role_permissions:

      composite_key:

        - role_id

        - permission_id

    admin_sessions:

      primary_key:

        session_id

      ttl: true

    admin_audit_logs:

      immutable: true

      partition:

        monthly

      indexes:

        - actor_id

        - workspace_id

        - request_id

        - created_at

    incidents:

      primary_key:

        incident_id

    feature_flags:

      primary_key:

        feature_flag_id

################################################################################
# PERFORMANCE TARGETS
################################################################################

performance:

  dashboard:

    p95:

      500ms

  workspace_search:

    p95:

      300ms

  user_search:

    p95:

      300ms

  audit_search:

    p95:

      800ms

  feature_flag_update:

    p95:

      200ms

  incident_creation:

    p95:

      500ms

################################################################################
# CACHE
################################################################################

cache:

  dashboard:

    ttl:

      30s

  permissions:

    ttl:

      5m

  feature_flags:

    ttl:

      60s

################################################################################
# RATE LIMITS
################################################################################

rate_limits:

  dashboard:

    60/min

  search:

    120/min

  exports:

    5/hour

  delete_workspace:

    2/hour

  secret_rotation:

    10/day

################################################################################
# ERROR CONTRACTS
################################################################################

errors:

  ADMIN-401:

    http:

      401

    description:

      Authentication failed

  ADMIN-402:

    http:

      403

    description:

      MFA required

  ADMIN-403:

    http:

      403

    description:

      Permission denied

  ADMIN-404:

    http:

      404

    description:

      Resource not found

  ADMIN-409:

    http:

      409

    description:

      Invalid state transition

  ADMIN-422:

    http:

      422

    description:

      Validation failed

  ADMIN-429:

    http:

      429

    description:

      Rate limit exceeded

  ADMIN-500:

    http:

      500

    description:

      Internal platform failure

################################################################################
# DECISION TABLE
################################################################################

decision_tables:

  WORKSPACE_SUSPEND:

    - if:

        permission: false

      then:

        ADMIN-403

    - if:

        workspace_missing: true

      then:

        ADMIN-404

    - if:

        workspace_active: false

      then:

        ADMIN-409

    - if:

        validation_failed: true

      then:

        ADMIN-422

    - if:

        all_checks_pass: true

      then:

        WORKFLOW-SUSPEND

################################################################################
# SECURITY CONSTRAINTS
################################################################################

security:

  immutable_rules:

    - admin_cannot_delete_audit_logs

    - admin_cannot_bypass_rbac

    - admin_cannot_disable_audit

    - admin_cannot_modify_own_permissions

    - admin_cannot_impersonate_platform_owner

    - admin_session_requires_mfa

    - admin_api_internal_only

################################################################################
# OBSERVABILITY
################################################################################

metrics:

  - admin_login_total

  - admin_login_failed

  - admin_action_total

  - permission_denied_total

  - workspace_suspend_total

  - incident_created_total

  - audit_write_latency

  - dashboard_latency

################################################################################
# REFERENCES
################################################################################

references:

  architecture:

    DOC-003

  database:

    DOC-004

  api:

    DOC-005

  security:

    DOC-006

  business_rules:

    DOC-007

  billing:

    DOC-013
################################################################################
# ACCEPTANCE TEST CATALOG
################################################################################

acceptance_tests:

  - id: ADMIN-TEST-001
    scenario: Admin Login
    given:
      - valid_credentials
      - mfa_completed
    when:
      - login_requested
    then:
      - session_created
      - jwt_issued
      - audit_created

  - id: ADMIN-TEST-002
    scenario: Invalid Credentials
    given:
      - invalid_password
    when:
      - login_requested
    then:
      - ADMIN-401

  - id: ADMIN-TEST-003
    scenario: MFA Missing
    given:
      - valid_credentials
      - mfa_not_completed
    when:
      - login_requested
    then:
      - ADMIN-402

  - id: ADMIN-TEST-004
    scenario: Suspend Workspace
    given:
      - workspace_active
      - permission_workspace_suspend
    when:
      - suspend_requested
    then:
      - workspace_suspended
      - sessions_revoked
      - audit_created

  - id: ADMIN-TEST-005
    scenario: Activate Workspace
    given:
      - workspace_suspended
    when:
      - activate_requested
    then:
      - workspace_active

  - id: ADMIN-TEST-006
    scenario: Reset Password
    given:
      - admin_permission
    when:
      - password_reset_requested
    then:
      - reset_link_generated
      - sessions_invalidated

  - id: ADMIN-TEST-007
    scenario: Force Logout
    given:
      - active_sessions
    when:
      - force_logout_requested
    then:
      - sessions_destroyed

  - id: ADMIN-TEST-008
    scenario: Rotate Secrets
    given:
      - security_permission
    when:
      - rotate_requested
    then:
      - previous_secret_invalid
      - audit_created

  - id: ADMIN-TEST-009
    scenario: Create Incident
    given:
      - incident_permission
    when:
      - incident_created
    then:
      - owner_assigned
      - notifications_sent

  - id: ADMIN-TEST-010
    scenario: Feature Flag Update
    given:
      - featureflag_permission
    when:
      - update_requested
    then:
      - cache_invalidated
      - rollout_updated

################################################################################
# INVARIANTS
################################################################################

invariants:

  - id: INV-ADMIN-001
    rule: Every admin action creates exactly one immutable audit record.

  - id: INV-ADMIN-002
    rule: Every privileged request passes RBAC validation before execution.

  - id: INV-ADMIN-003
    rule: Audit logs cannot be deleted.

  - id: INV-ADMIN-004
    rule: Platform Owner role cannot be deleted.

  - id: INV-ADMIN-005
    rule: No administrator can grant permissions greater than their own.

  - id: INV-ADMIN-006
    rule: Workspace deletion cannot bypass retention policy.

  - id: INV-ADMIN-007
    rule: Feature flag updates propagate to every running instance.

################################################################################
# IMPLEMENTATION CONSTRAINTS
################################################################################

implementation:

  backend:

    framework:

      Spring Boot

  frontend:

    framework:

      Next.js

  database:

    PostgreSQL

  cache:

    Redis

  queue:

    Redis Streams

  storage:

    Supabase Storage

  authentication:

    JWT

  authorization:

    RBAC

################################################################################
# SCALE PATH
################################################################################

scale:

  phase_1:

    customers:

      10

    architecture:

      monolith

    database:

      single_postgres

    cache:

      optional

  phase_2:

    customers:

      50

    additions:

      - redis

      - background_workers

  phase_3:

    customers:

      100

    additions:

      - dedicated_job_workers
      - monitoring

  phase_4:

    customers:

      1000

    additions:

      - read_replicas
      - horizontal_api_scaling
      - queue_partitioning

  phase_5:

    customers:

      10000

    additions:

      - dedicated_cache_cluster
      - dedicated_worker_cluster
      - autoscaling

  phase_6:

    customers:

      100000

    additions:

      - multi_region
      - distributed_queue
      - sharding_if_required

################################################################################
# NON GOALS
################################################################################

non_goals:

  - kubernetes_required_for_v1

  - microservices_required_for_v1

  - event_sourcing_required_for_v1

  - distributed_database_required_for_v1

################################################################################
# CURSOR CONTRACT
################################################################################

cursor:

  canonical_module:

    ADMIN

  generated_code_must_not:

    - bypass_rbac

    - bypass_audit

    - hardcode_permissions

    - duplicate_business_rules

    - expose_internal_admin_api

  generated_code_must:

    - reference_permission_catalog

    - reference_workflows

    - reference_state_machine

    - reference_error_contracts

    - emit_events

################################################################################
# DOCUMENT STATUS
################################################################################

status:

  completion:

    COMPLETE

  ready_for_cursor:

    true

  implementation_dependency:

    implementation/00_FOUNDATION.md

################################################################################
# END OF FILE
################################################################################   