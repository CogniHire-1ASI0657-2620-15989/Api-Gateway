from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.config import get_settings
from app.proxy import forward_request
from app.schemas import GenerateLearningPathRequest
from app.security import get_current_user_id


router = APIRouter(prefix="/api/v1/learning-paths", tags=["Learning Pathway"])


def _identity_header(user_id: int) -> dict[str, str]:
    settings = get_settings()
    return {settings.gateway_user_id_header: str(user_id)}


@router.post("", status_code=201)
async def generate_learning_path(
    _: GenerateLearningPathRequest, request: Request, user_id: int = Depends(get_current_user_id)
) -> Response:
    return await forward_request(
        request,
        get_settings().learning_pathway_service_url,
        "/api/v1/learning-paths",
        _identity_header(user_id),
    )


@router.get("/{job_id}")
async def get_learning_path(job_id: int, request: Request, user_id: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(
        request,
        get_settings().learning_pathway_service_url,
        f"/api/v1/learning-paths/{job_id}",
        _identity_header(user_id),
    )


@router.patch("/{learning_path_id}/items/{item_id}")
async def mark_learning_path_item_watched(
    learning_path_id: int, item_id: int, request: Request, user_id: int = Depends(get_current_user_id)
) -> Response:
    return await forward_request(
        request,
        get_settings().learning_pathway_service_url,
        f"/api/v1/learning-paths/{learning_path_id}/items/{item_id}",
        _identity_header(user_id),
    )


@router.get("/{learning_path_id}/progress")
async def get_learning_path_progress(
    learning_path_id: int, request: Request, user_id: int = Depends(get_current_user_id)
) -> Response:
    return await forward_request(
        request,
        get_settings().learning_pathway_service_url,
        f"/api/v1/learning-paths/{learning_path_id}/progress",
        _identity_header(user_id),
    )
