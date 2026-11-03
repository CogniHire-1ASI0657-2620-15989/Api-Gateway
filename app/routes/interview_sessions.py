from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.config import get_settings
from app.proxy import forward_request
from app.schemas import StartInterviewRequest, SubmitInterviewResponseRequest
from app.security import get_current_user_id


router = APIRouter(prefix="/api/v1/interview-sessions", tags=["Interview Coach"])


def _identity_header(user_id: int) -> dict[str, str]:
    settings = get_settings()
    return {settings.gateway_user_id_header: str(user_id)}


@router.post("", status_code=201)
async def start_interview(
    _: StartInterviewRequest,
    request: Request,
    user_id: int = Depends(get_current_user_id),
) -> Response:
    return await forward_request(
        request,
        get_settings().interview_coach_service_url,
        "/api/v1/interview-sessions",
        _identity_header(user_id),
    )


@router.post("/{session_id}/messages")
async def submit_response(
    session_id: int,
    _: SubmitInterviewResponseRequest,
    request: Request,
    user_id: int = Depends(get_current_user_id),
) -> Response:
    return await forward_request(
        request,
        get_settings().interview_coach_service_url,
        f"/api/v1/interview-sessions/{session_id}/messages",
        _identity_header(user_id),
    )


@router.post("/{session_id}/complete")
async def complete_interview(session_id: int, request: Request, user_id: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(
        request,
        get_settings().interview_coach_service_url,
        f"/api/v1/interview-sessions/{session_id}/complete",
        _identity_header(user_id),
    )


@router.get("")
async def list_interview_sessions(request: Request, user_id: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(
        request,
        get_settings().interview_coach_service_url,
        "/api/v1/interview-sessions",
        _identity_header(user_id),
    )


@router.get("/{session_id}")
async def get_interview_session(session_id: int, request: Request, user_id: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(
        request,
        get_settings().interview_coach_service_url,
        f"/api/v1/interview-sessions/{session_id}",
        _identity_header(user_id),
    )
