"""Authentication controllers. No business logic lives here (RULE API-005)."""

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.core.config import settings
from app.core.deps import AuthContext, get_auth_context
from app.core.errors import AppError
from app.core.rate_limit import enforce
from app.modules.auth import service
from app.modules.auth.schemas import (
    ForgotPasswordRequest,
    GoogleLoginRequest,
    LoginRequest,
    MeResponse,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionSummary,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

REFRESH_COOKIE_NAME = "ganaka_refresh_token"
REFRESH_COOKIE_PATH = f"{settings.API_PREFIX}/auth/refresh"


def _set_refresh_cookie(response: Response, raw_refresh: str) -> None:
    """TOKEN_TRANSPORT: refresh token only, httpOnly + Secure + SameSite=Strict,
    scoped to the refresh path. The access token is never cookie-transported."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_refresh,
        max_age=settings.REFRESH_TOKEN_TTL_DAYS * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=True,
        samesite="strict",
    )


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
    description="Public. Creates a user, their first workspace and sends an email verification link. "
    "Returns the same response whether or not the email already exists.",
)
async def register(payload: RegisterRequest, request: Request):
    await enforce("auth.register", request)
    return await service.register(payload, request)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Sign in with email and password",
    description="Public. Returns an access token in the body and sets the refresh token cookie.",
)
async def login(payload: LoginRequest, request: Request, response: Response):
    await enforce("auth.login", request)
    await enforce("auth.login", request, subject=payload.email.lower())
    result, raw_refresh = await service.login(payload, request)
    _set_refresh_cookie(response, raw_refresh)
    return result


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Sign in with Google",
    description="Public. Verifies a Google ID token (audience, issuer and email_verified claim).",
)
async def google_login(payload: GoogleLoginRequest, request: Request, response: Response):
    await enforce("auth.google", request)
    result, raw_refresh = await service.google_login(payload.id_token, request)
    _set_refresh_cookie(response, raw_refresh)
    return result


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate the refresh token and mint a new access token",
    description="Public (proof of possession is the refresh token itself). Reads the refresh token "
    "from the httpOnly cookie, or from the body for non-browser clients.",
)
async def refresh(request: Request, response: Response, payload: RefreshRequest | None = None):
    await enforce("auth.refresh", request)
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME) or (payload.refresh_token if payload else None)
    if not raw_refresh:
        raise AppError("AUTH-003")
    result, new_refresh = await service.refresh(raw_refresh, request)
    _set_refresh_cookie(response, new_refresh)
    return result


@router.post("/logout", response_model=MessageResponse, summary="Sign out of the current session")
async def logout(request: Request, response: Response, context: AuthContext = Depends(get_auth_context)):
    result = await service.logout(context, request)
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
    return result


@router.post("/logout-all", response_model=MessageResponse, summary="Sign out of every session")
async def logout_all(request: Request, response: Response, context: AuthContext = Depends(get_auth_context)):
    result = await service.logout_all(context, request)
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
    return result


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request a password reset link",
    description="Public. Always returns the same response so account existence is not disclosed.",
)
async def forgot_password(payload: ForgotPasswordRequest, request: Request):
    await enforce("auth.forgot_password", request)
    return await service.forgot_password(payload.email, request)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Set a new password using a reset token",
    description="Public. Invalidates every active session on success.",
)
async def reset_password(payload: ResetPasswordRequest, request: Request):
    await enforce("auth.reset_password", request)
    return await service.reset_password(payload.token, payload.password, request)


@router.get(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify an email address",
    description="Public. Single-use token, valid for 24 hours.",
)
async def verify_email(request: Request, token: str = Query(min_length=10)):
    await enforce("auth.verify_email", request)
    return await service.verify_email(token, request)


@router.get("/me", response_model=MeResponse, summary="Current user, workspace and resolved permissions")
async def me(context: AuthContext = Depends(get_auth_context)):
    return await service.me(context)


@router.get("/sessions", response_model=list[SessionSummary], summary="List the current user's active sessions")
async def list_sessions(context: AuthContext = Depends(get_auth_context)):
    return await service.list_sessions(context)


@router.delete("/sessions/{session_id}", response_model=MessageResponse, summary="Revoke one of your sessions")
async def revoke_session(session_id: str, request: Request, context: AuthContext = Depends(get_auth_context)):
    return await service.revoke_session(context, session_id, request)
