from collections.abc import Mapping

import httpx
from fastapi import HTTPException, Request, status
from fastapi.responses import Response

from app.config import get_settings


_HOP_BY_HOP_HEADERS = {
    "connection",
    "content-encoding",
    "content-length",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
}


async def forward_request(
    request: Request,
    base_url: str,
    path: str,
    extra_headers: Mapping[str, str] | None = None,
) -> Response:
    """Forward one public request while preventing client identity-header spoofing."""
    protected_headers = {"x-user-id", "x-internal-api-key", "accept-encoding"}
    if extra_headers:
        protected_headers.update(name.lower() for name in extra_headers)
    headers = {
        name: value
        for name, value in request.headers.items()
        if name.lower() not in _HOP_BY_HOP_HEADERS and name.lower() not in protected_headers
    }
    if extra_headers:
        headers.update(extra_headers)
    headers["X-Internal-Api-Key"] = get_settings().internal_api_key
    # Render can compress calls that traverse its public edge. Requesting the
    # identity encoding prevents a compressed body from being relayed as JSON.
    headers["Accept-Encoding"] = "identity"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            upstream = await client.request(
                request.method,
                f"{base_url}{path}",
                params=list(request.query_params.multi_items()),
                content=await request.body(),
                headers=headers,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="El microservicio solicitado no está disponible.",
        ) from exc

    response_headers = {
        name: value
        for name, value in upstream.headers.items()
        if name.lower() not in _HOP_BY_HOP_HEADERS
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )
