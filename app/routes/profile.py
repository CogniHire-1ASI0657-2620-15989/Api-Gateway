from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.config import get_settings
from app.proxy import forward_request
from app.schemas import ChangePasswordRequest, SkillRequest, UpdateProfileRequest
from app.security import get_current_user_id


router = APIRouter(prefix="/api/v1/profile", tags=["Identity"])


def _identity_url() -> str:
    return get_settings().identity_service_url


@router.get("/me")
async def get_profile(request: Request, _: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(request, _identity_url(), "/api/v1/profile/me")


@router.put("/me")
async def update_profile(_: UpdateProfileRequest, request: Request, __: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(request, _identity_url(), "/api/v1/profile/me")


@router.put("/me/password")
async def change_password(_: ChangePasswordRequest, request: Request, __: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(request, _identity_url(), "/api/v1/profile/me/password")


@router.post("/me/skills/{skill_type}")
async def add_skill(skill_type: str, _: SkillRequest, request: Request, __: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(request, _identity_url(), f"/api/v1/profile/me/skills/{skill_type}")


@router.put("/me/skills/{skill_type}/{skill_name}")
async def update_skill(skill_type: str, skill_name: str, _: SkillRequest, request: Request, __: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(request, _identity_url(), f"/api/v1/profile/me/skills/{skill_type}/{skill_name}")


@router.delete("/me/skills/{skill_type}/{skill_name}")
async def remove_skill(skill_type: str, skill_name: str, request: Request, _: int = Depends(get_current_user_id)) -> Response:
    return await forward_request(request, _identity_url(), f"/api/v1/profile/me/skills/{skill_type}/{skill_name}")
