"""Canonical error registry and global exception handling.

Codes follow docs/09_ERROR_CATALOG.md. Codes marked EXTENDED are additive
entries required by implementation/01_AUTHENTICATION.md,
implementation/02_WORKSPACE_AND_RBAC.md and implementation/04_SHOPIFY.md ERRORS
sections, which name errors the catalog had not yet assigned codes to. They
reuse the catalog's categories and response envelope; no new format is
introduced.
"""

import logging
from datetime import datetime, timezone

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("ganaka.errors")

ERROR_REGISTRY = {
    # --- AUTH (docs/09 ERR-001..003) ---
    "AUTH-001": (status.HTTP_401_UNAUTHORIZED, "Invalid email or password."),
    "AUTH-002": (status.HTTP_401_UNAUTHORIZED, "JWT token expired."),
    "AUTH-003": (status.HTTP_401_UNAUTHORIZED, "Invalid authentication token."),
    # --- AUTH (EXTENDED) ---
    "AUTH-004": (status.HTTP_403_FORBIDDEN, "Email address is not verified."),
    "AUTH-005": (status.HTTP_403_FORBIDDEN, "Account is temporarily locked."),
    "AUTH-006": (status.HTTP_401_UNAUTHORIZED, "Session expired."),
    "AUTH-007": (status.HTTP_404_NOT_FOUND, "User not found."),
    "AUTH-008": (status.HTTP_409_CONFLICT, "Additional verification is required before this sign-in method can be used."),
    "AUTH-009": (status.HTTP_400_BAD_REQUEST, "This link is invalid or has expired."),
    "AUTH-010": (status.HTTP_400_BAD_REQUEST, "Password does not meet the password policy."),
    "AUTH-011": (status.HTTP_403_FORBIDDEN, "Account is disabled."),
    # --- AUTHZ (ERR-004) ---
    "AUTHZ-001": (status.HTTP_403_FORBIDDEN, "Access denied."),
    # --- WORKSPACE (ERR-005..006) ---
    "WORKSPACE-001": (status.HTTP_404_NOT_FOUND, "Workspace not found."),
    "WORKSPACE-002": (status.HTTP_403_FORBIDDEN, "Workspace access denied."),
    # --- WORKSPACE (EXTENDED) ---
    "WORKSPACE-003": (status.HTTP_409_CONFLICT, "Member already exists."),
    "WORKSPACE-004": (status.HTTP_400_BAD_REQUEST, "Invalid invitation."),
    "WORKSPACE-005": (status.HTTP_400_BAD_REQUEST, "Invitation expired."),
    "WORKSPACE-006": (status.HTTP_403_FORBIDDEN, "Workspace owner privileges are required."),
    "WORKSPACE-007": (status.HTTP_403_FORBIDDEN, "Cross workspace access denied."),
    "WORKSPACE-008": (status.HTTP_404_NOT_FOUND, "Role not found."),
    "WORKSPACE-009": (status.HTTP_409_CONFLICT, "Role limit exceeded."),
    "WORKSPACE-010": (status.HTTP_404_NOT_FOUND, "Member not found."),
    "WORKSPACE-011": (status.HTTP_409_CONFLICT, "System roles cannot be modified."),
    # --- SHOPIFY (ERR-009 + EXTENDED) ---
    "SHOPIFY-001": (status.HTTP_502_BAD_GATEWAY, "Shopify synchronization failed."),
    "SHOPIFY-002": (status.HTTP_400_BAD_REQUEST, "Invalid shop domain."),
    "SHOPIFY-003": (status.HTTP_502_BAD_GATEWAY, "Shopify OAuth failed."),
    "SHOPIFY-004": (status.HTTP_400_BAD_REQUEST, "Invalid OAuth state."),
    "SHOPIFY-005": (status.HTTP_409_CONFLICT, "Store already connected."),
    "SHOPIFY-006": (status.HTTP_404_NOT_FOUND, "Store not connected."),
    "SHOPIFY-007": (status.HTTP_401_UNAUTHORIZED, "Invalid webhook signature."),
    "SHOPIFY-008": (status.HTTP_502_BAD_GATEWAY, "Shopify API error."),
    # --- RAZORPAY (EXTENDED) ---
    # ARCH-AUDIT fix: these codes were raised throughout app/modules/shopify/
    # service.py but were never registered, so every Razorpay error path
    # crashed with an unhandled KeyError instead of returning a proper
    # response. Registered here with the same status/semantics the call
    # sites already implied.
    "RAZORPAY-005": (status.HTTP_409_CONFLICT, "Razorpay account already connected."),
    "RAZORPAY-006": (status.HTTP_404_NOT_FOUND, "Razorpay account not connected."),
    "RAZORPAY-007": (status.HTTP_401_UNAUTHORIZED, "Invalid webhook signature."),
    "RAZORPAY-008": (status.HTTP_502_BAD_GATEWAY, "Razorpay API error."),
    "RAZORPAY-009": (status.HTTP_401_UNAUTHORIZED, "Invalid Razorpay API credentials."),
    # --- EXPORTS (ARCH-AUDIT-002 fix) ---
    "EXPORT-001": (status.HTTP_404_NOT_FOUND, "Export not found or has expired."),
    # --- VALIDATION (ERR-007..008) ---
    "VALIDATION-001": (status.HTTP_400_BAD_REQUEST, "Validation failed."),
    "VALIDATION-002": (status.HTTP_400_BAD_REQUEST, "Invalid UUID format."),
    # --- RATE LIMIT (ERR-017) ---
    "RATE_LIMIT-001": (status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests."),
    # --- EXTERNAL / SYSTEM / UNKNOWN (ERR-018..020) ---
    "EXTERNAL-001": (status.HTTP_503_SERVICE_UNAVAILABLE, "External service unavailable."),
    "DATABASE-001": (status.HTTP_500_INTERNAL_SERVER_ERROR, "Database operation failed."),
    "SYSTEM-001": (status.HTTP_500_INTERNAL_SERVER_ERROR, "Unexpected internal error."),
    "UNKNOWN-001": (status.HTTP_500_INTERNAL_SERVER_ERROR, "Unexpected error occurred."),
}


class AppError(Exception):
    """Domain error carrying a catalog code. Never carries internal details."""

    def __init__(self, code: str, message: str | None = None, details: list | None = None):
        if code not in ERROR_REGISTRY:
            raise KeyError(f"Unregistered error code: {code}")
        self.code = code
        self.status_code, default_message = ERROR_REGISTRY[code]
        self.message = message or default_message
        self.details = details
        super().__init__(self.message)


def _envelope(request: Request, status_code: int, code: str, message: str, details=None) -> JSONResponse:
    body = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status_code,
        "code": code,
        "message": message,
        "path": request.url.path,
        "requestId": getattr(request.state, "request_id", ""),
    }
    if details:
        body["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        return _envelope(request, exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(p) for p in err.get("loc", [])[1:]), "issue": err.get("msg", "")}
            for err in exc.errors()
        ]
        code, message = ERROR_REGISTRY["VALIDATION-001"][0], ERROR_REGISTRY["VALIDATION-001"][1]
        return _envelope(request, code, "VALIDATION-001", message, details)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        mapping = {
            401: "AUTH-003",
            403: "AUTHZ-001",
            429: "RATE_LIMIT-001",
        }
        code = mapping.get(exc.status_code, "UNKNOWN-001")
        message = ERROR_REGISTRY[code][1] if exc.status_code in mapping else str(exc.detail)
        return _envelope(request, exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        # EH-004: always log internally, never expose internals to the client.
        logger.exception("unhandled_exception request_id=%s path=%s", getattr(request.state, "request_id", ""), request.url.path)
        status_code, message = ERROR_REGISTRY["SYSTEM-001"]
        return _envelope(request, status_code, "SYSTEM-001", message)
