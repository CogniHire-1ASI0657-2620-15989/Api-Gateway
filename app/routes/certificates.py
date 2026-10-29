from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.config import get_settings
from app.proxy import forward_request
from app.security import get_current_user_id


router = APIRouter(prefix="/api/v1/certificates", tags=["Certificates"])


def _identity_header(user_id: int) -> dict[str, str]:
    settings = get_settings()
    return {settings.gateway_user_id_header: str(user_id)}


@router.post("")
async def upload_certificate(request: Request, user_id: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(
        request,
        get_settings().learning_pathway_service_url,
        "/api/v1/certificates",
        _identity_header(user_id),
    )


@router.get("/{certificate_id}")
async def get_certificate(certificate_id: int, request: Request, user_id: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(
        request,
        get_settings().learning_pathway_service_url,
        f"/api/v1/certificates/{certificate_id}",
        _identity_header(user_id),
    )


@router.post("/{certificate_id}/synchronization")
async def synchronize_certificate(certificate_id: int, request: Request, user_id: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(
        request,
        get_settings().learning_pathway_service_url,
        f"/api/v1/certificates/{certificate_id}/synchronization",
        _identity_header(user_id),
    )
