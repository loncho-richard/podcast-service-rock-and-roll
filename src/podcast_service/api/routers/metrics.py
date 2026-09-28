from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(tags=["observability"])


@router.get(
    "/metrics",
    summary="Prometheus metrics (public)",
    description=(
        "HTTP traffic by route, ingestion outcomes, third-party call results and offline "
        "fallbacks, in the Prometheus text format. Public like `/health`: in production it "
        "would only be reachable from the internal network (see NOTES.md)."
    ),
    response_class=Response,
    responses={200: {"content": {CONTENT_TYPE_LATEST: {}}, "description": "Metrics."}},
)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
