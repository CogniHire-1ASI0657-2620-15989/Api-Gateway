import json
import logging
import os
import time
import uuid
from contextvars import ContextVar
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


CORRELATION_ID_HEADER = "X-Correlation-ID"
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def outbound_headers(headers: dict[str, str] | None = None) -> dict[str, str]:
    result = {
        name: value
        for name, value in (headers or {}).items()
        if name.lower() != CORRELATION_ID_HEADER.lower()
    }
    correlation_id = get_correlation_id()
    if correlation_id:
        result[CORRELATION_ID_HEADER] = correlation_id
    return result


class JsonFormatter(logging.Formatter):
    converter = time.gmtime

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "service": getattr(record, "service", "unknown"),
            "event": record.getMessage(),
        }
        for field in ("correlation_id", "method", "path", "status_code", "duration_ms", "error_type"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class ServiceLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        kwargs["extra"] = {**self.extra, **kwargs.get("extra", {})}
        return msg, kwargs


def configure_logging(service_name: str) -> logging.Logger:
    logger = logging.getLogger("pathbridge")
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    logger.propagate = False
    if not any(getattr(handler, "_pathbridge_json", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        handler._pathbridge_json = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    return ServiceLoggerAdapter(logger, {"service": service_name})  # type: ignore[return-value]


def problem_response(
    request: Request,
    *,
    status_code: int,
    title: str,
    detail: str,
    problem_type: str,
    errors: object | None = None,
) -> JSONResponse:
    correlation_id = get_correlation_id()
    body: dict[str, object] = {
        "type": problem_type,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": request.url.path,
    }
    if correlation_id:
        body["correlation_id"] = correlation_id
    if errors is not None:
        body["errors"] = jsonable_encoder(errors)
    headers = {CORRELATION_ID_HEADER: correlation_id} if correlation_id else None
    return JSONResponse(
        status_code=status_code,
        content=body,
        media_type="application/problem+json",
        headers=headers,
    )


def install_observability(app: FastAPI, service_name: str) -> None:
    logger = configure_logging(service_name)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        try:
            title = HTTPStatus(exc.status_code).phrase
        except ValueError:
            title = "Request failed"
        detail = exc.detail if isinstance(exc.detail, str) else title
        return problem_response(
            request,
            status_code=exc.status_code,
            title=title,
            detail=detail,
            problem_type=f"urn:pathbridge:problem:http-{exc.status_code}",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return problem_response(
            request,
            status_code=422,
            title="Validation failed",
            detail="The request could not be validated.",
            problem_type="urn:pathbridge:problem:validation",
            errors=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "request_failed",
            extra={
                "correlation_id": get_correlation_id(),
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "error_type": type(exc).__name__,
            },
        )
        return problem_response(
            request,
            status_code=500,
            title="Internal Server Error",
            detail="An unexpected error occurred.",
            problem_type="urn:pathbridge:problem:internal-server-error",
        )

    @app.middleware("http")
    async def observe_request(request: Request, call_next):
        incoming_id = request.headers.get(CORRELATION_ID_HEADER)
        try:
            correlation_id = str(uuid.UUID(incoming_id)) if incoming_id else str(uuid.uuid4())
        except (TypeError, ValueError, AttributeError):
            correlation_id = str(uuid.uuid4())
        token = _correlation_id.set(correlation_id)
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            logger.info(
                "request_completed",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                },
            )
            return response
        finally:
            _correlation_id.reset(token)
