import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    identity_service_url: str
    job_discovery_service_url: str
    gap_analysis_service_url: str
    jwt_secret_key: str
    jwt_issuer: str
    jwt_audience: str
    gateway_user_id_header: str
    cors_origins: list[str]


@lru_cache
def get_settings() -> Settings:
    required = {
        "IDENTITY_SERVICE_URL": os.getenv("IDENTITY_SERVICE_URL"),
        "JOB_DISCOVERY_SERVICE_URL": os.getenv("JOB_DISCOVERY_SERVICE_URL"),
        "GAP_ANALYSIS_SERVICE_URL": os.getenv("GAP_ANALYSIS_SERVICE_URL"),
        "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY"),
        "JWT_ISSUER": os.getenv("JWT_ISSUER"),
        "JWT_AUDIENCE": os.getenv("JWT_AUDIENCE"),
    }
    missing = [name for name, value in required.items() if not value or not value.strip()]
    if missing:
        raise RuntimeError(f"Missing required configuration: {', '.join(missing)}")

    origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]
    return Settings(
        identity_service_url=required["IDENTITY_SERVICE_URL"].rstrip("/"),
        job_discovery_service_url=required["JOB_DISCOVERY_SERVICE_URL"].rstrip("/"),
        gap_analysis_service_url=required["GAP_ANALYSIS_SERVICE_URL"].rstrip("/"),
        jwt_secret_key=required["JWT_SECRET_KEY"],
        jwt_issuer=required["JWT_ISSUER"],
        jwt_audience=required["JWT_AUDIENCE"],
        gateway_user_id_header=os.getenv("GATEWAY_USER_ID_HEADER", "X-User-Id").strip(),
        cors_origins=origins,
    )
