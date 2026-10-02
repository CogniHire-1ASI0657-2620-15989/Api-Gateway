from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    segment: str
    city: str | None = None
    country: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class PasswordRecoveryRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    token: str = Field(min_length=20)
    new_password: str = Field(min_length=6, max_length=128)


class SkillRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    level: str | None = Field(default=None, max_length=50)


class EducationRequest(BaseModel):
    degree: str | None = Field(default=None, max_length=150)
    institution: str | None = Field(default=None, max_length=150)
    field_of_study: str | None = Field(default=None, max_length=150)
    start_year: int | None = Field(default=None, ge=1900, le=2100)
    end_year: int | None = Field(default=None, ge=1900, le=2100)


class ExperienceRequest(BaseModel):
    position: str | None = Field(default=None, max_length=150)
    company: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    start_date: str | None = Field(default=None, max_length=20)
    end_date: str | None = Field(default=None, max_length=20)
    current: bool = False


class LanguageRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    level: str | None = Field(default=None, max_length=50)


class UpdateProfileRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    email: EmailStr | None = None
    segment: str | None = None
    city: str | None = None
    country: str | None = None
    target_position: str | None = Field(default=None, max_length=150)
    expected_city: str | None = Field(default=None, max_length=100)
    expected_country: str | None = Field(default=None, max_length=100)
    work_modality: Literal["remoto", "hibrido", "presencial"] | None = None
    hard_skills: list[SkillRequest] | None = None
    soft_skills: list[SkillRequest] | None = None
    education: list[EducationRequest] | None = None
    experience: list[ExperienceRequest] | None = None
    languages: list[LanguageRequest] | None = None
    professional_summary: str | None = Field(default=None, max_length=2000)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


class GenerateGapReportRequest(BaseModel):
    job_id: int = Field(gt=0)
