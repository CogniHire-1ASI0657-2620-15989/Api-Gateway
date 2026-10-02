from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import auth, gap_reports, jobs, profile


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings()
    yield


app = FastAPI(
    title="PathBridge API Gateway",
    description="Punto de entrada público para los microservicios de PathBridge.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(jobs.router)
app.include_router(gap_reports.router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"service": "api-gateway", "status": "healthy"}
