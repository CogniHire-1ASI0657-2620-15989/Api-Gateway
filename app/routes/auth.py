from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.config import get_settings
from app.proxy import forward_request
from app.schemas import LoginRequest, PasswordRecoveryRequest, PasswordResetRequest, RegisterUserRequest


router = APIRouter(prefix="/api/v1/auth", tags=["Identity"])


@router.post("/register", status_code=201)
async def register(_: RegisterUserRequest, request: Request) -> Response:
    return await forward_request(request, get_settings().identity_service_url, "/api/v1/auth/register")


@router.post("/login")
async def login(_: LoginRequest, request: Request) -> Response:
    return await forward_request(request, get_settings().identity_service_url, "/api/v1/auth/login")


@router.post("/password-recovery")
async def password_recovery(_: PasswordRecoveryRequest, request: Request) -> Response:
    return await forward_request(request, get_settings().identity_service_url, "/api/v1/auth/password-recovery")


@router.post("/password-reset", status_code=204)
async def password_reset(_: PasswordResetRequest, request: Request) -> Response:
    return await forward_request(request, get_settings().identity_service_url, "/api/v1/auth/password-reset")
