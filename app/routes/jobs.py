from enum import IntEnum

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from app.config import get_settings
from app.proxy import forward_request
from app.security import get_current_user_id


router = APIRouter(prefix="/api/v1", tags=["Job Discovery"])


class RadiusKm(IntEnum):
    ZERO = 0
    FOUR = 4
    EIGHT = 8
    SIXTEEN = 16
    TWENTY_SIX = 26
    FORTY = 40
    EIGHTY = 80


def _identity_header(user_id: int) -> dict[str, str]:
    settings = get_settings()
    return {settings.gateway_user_id_header: str(user_id)}


@router.get("/jobs")
async def search_jobs(
    request: Request,
    user_id: int = Depends(get_current_user_id),
    keywords: str = Query(min_length=1, max_length=200),
    location: str = Query(min_length=1, max_length=200),
    page: int = Query(default=1, ge=1, le=3),
    page_size: int = Query(default=10, ge=1, le=20),
    radius_km: RadiusKm = RadiusKm.ZERO,
) -> Response:
    return await forward_request(request, get_settings().job_discovery_service_url, "/api/v1/jobs", _identity_header(user_id))


@router.get("/jobs/{job_id}")
async def get_job(job_id: int, request: Request, user_id: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(request, get_settings().job_discovery_service_url, f"/api/v1/jobs/{job_id}", _identity_header(user_id))


@router.post("/jobs/{job_id}/favorite")
async def add_favorite(job_id: int, request: Request, user_id: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(request, get_settings().job_discovery_service_url, f"/api/v1/jobs/{job_id}/favorite", _identity_header(user_id))


@router.delete("/jobs/{job_id}/favorite", status_code=204)
async def remove_favorite(job_id: int, request: Request, user_id: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(request, get_settings().job_discovery_service_url, f"/api/v1/jobs/{job_id}/favorite", _identity_header(user_id))


@router.get("/favorites")
async def list_favorites(
    request: Request,
    user_id: int = Depends(get_current_user_id),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
) -> Response:
    return await forward_request(request, get_settings().job_discovery_service_url, "/api/v1/favorites", _identity_header(user_id))
