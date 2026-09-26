from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from podcast_service.domain.podcast.repository import PodcastRepository


class UnitOfWork(ABC):
    """Transaction boundary for a use case.

    Usage: `async with uow_factory() as uow: ...; await uow.commit()`.
    Leaving the block without committing rolls back.
    """

    podcasts: PodcastRepository

    @abstractmethod
    async def __aenter__(self) -> Self: ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...
