from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from podcast_service.api.errors import ERROR_RESPONSES
from podcast_service.api.schemas.auth import TokenResponse
from podcast_service.application.auth.issue_token import IssueAccessToken
from podcast_service.container import Container

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/token",
    summary="Exchange client credentials for an access token (public)",
    description=(
        "OAuth2 password-style form: send the client id as `username` and the client "
        "secret as `password`. Use the returned token as `Authorization: Bearer <token>`."
    ),
    responses=ERROR_RESPONSES,
)
@inject
async def issue_token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    issue_access_token: IssueAccessToken = Depends(Provide[Container.issue_access_token]),
) -> TokenResponse:
    token = issue_access_token.execute(client_id=form.username, client_secret=form.password)
    return TokenResponse(access_token=token.token, expires_in=token.expires_in)
