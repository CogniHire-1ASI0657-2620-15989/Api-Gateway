from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.config import get_settings
from app.proxy import forward_request
from app.schemas import GenerateGapReportRequest
from app.security import get_current_user_id


router = APIRouter(prefix="/api/v1/gap-reports", tags=["Gap Analysis"])


def _identity_header(user_id: int) -> dict[str, str]:
    settings = get_settings()
    return {settings.gateway_user_id_header: str(user_id)}


@router.post("", status_code=201)
async def generate_report(_: GenerateGapReportRequest, request: Request, user_id: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(request, get_settings().gap_analysis_service_url, "/api/v1/gap-reports", _identity_header(user_id))


@router.get("/{job_id}")
async def get_report(job_id: int, request: Request, user_id: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(request, get_settings().gap_analysis_service_url, f"/api/v1/gap-reports/{job_id}", _identity_header(user_id))


@router.get("")
async def list_reports(request: Request, user_id: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(request, get_settings().gap_analysis_service_url, "/api/v1/gap-reports", _identity_header(user_id))
