"""
API Key authentication dependency.
Usage:
    from api.auth import require_api_key
    @router.get("/endpoint", dependencies=[Depends(require_api_key)])

Set API_KEY=your-secret in .env to enable.
If API_KEY is empty, auth is disabled (useful for local dev).
"""
from fastapi import Header, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(x_api_key: str | None = Security(_api_key_header)) -> None:
    """
    FastAPI dependency. Validates the X-API-Key header.
    - If API_KEY is not set in .env → auth is disabled, all requests pass through.
    - If API_KEY is set → header must match exactly, else 401.
    """
    configured_key = settings.api_key
    if not configured_key:
        return  # dev mode — no key configured, open access

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Pass X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if x_api_key != configured_key:
        raise HTTPException(
            status_code=403,
            detail="Invalid API key.",
        )
