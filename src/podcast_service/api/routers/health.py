from http import HTTPStatus

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Response

from podcast_service.api.schemas import HealthResponse
from podcast_service.container import Container
from podcast_service.infrastructure.persistence import DatabaseHealthProbe

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Service and database health (public)",
    responses={HTTPStatus.SERVICE_UNAVAILABLE: {"model": HealthResponse}},
)
@inject
async def health(
    response: Response,
    probe: DatabaseHealthProbe = Depends(Provide[Container.database_health_probe]),
) -> HealthResponse:
    if await probe.is_healthy():
        return HealthResponse(status="ok", database="ok")
    response.status_code = HTTPStatus.SERVICE_UNAVAILABLE.value
    return HealthResponse(status="degraded", database="unavailable")
