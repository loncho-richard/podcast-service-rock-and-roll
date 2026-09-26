from fastapi import APIRouter

from podcast_service.api.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness check (public)")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
