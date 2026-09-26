from collections.abc import AsyncIterator
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import (
    ColumnElement,
    RowMapping,
    Select,
    Table,
    and_,
    func,
    literal_column,
    or_,
    select,
    tuple_,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from podcast_service.domain.podcast.entities import Podcast
from podcast_service.domain.podcast.filters import Page, PageRequest, PodcastFilters
from podcast_service.domain.podcast.repository import PodcastRepository, UpsertOutcome
from podcast_service.domain.podcast.value_objects import ColorPalette, ExternalRef
from podcast_service.infrastructure.persistence.models import PodcastModel

_TABLE = cast(Table, PodcastModel.__table__)
_STREAM_BATCH_SIZE = 500
# Columns overwritten by a re-ingestion; identity and audit columns are left alone.
_MUTABLE_COLUMNS = (
    "title",
    "author",
    "description",
    "language",
    "country",
    "genres",
    "primary_genre",
    "feed_url",
    "store_url",
    "cover_image_url",
    "palette",
    "explicit",
    "episode_count",
    "released_at",
)


class SqlAlchemyPodcastRepository(PodcastRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, podcast: Podcast) -> tuple[Podcast, UpsertOutcome]:
        values = _to_row(podcast)
        insert_stmt = insert(_TABLE).values(id=uuid4(), **values)
        excluded = insert_stmt.excluded
        stmt = insert_stmt.on_conflict_do_update(
            constraint="uq_podcasts_source_external_id",
            set_={**{name: excluded[name] for name in _MUTABLE_COLUMNS}, "updated_at": func.now()},
            # Only touch the row when something actually changed.
            where=tuple_(*(_TABLE.c[name] for name in _MUTABLE_COLUMNS)).is_distinct_from(
                tuple_(*(excluded[name] for name in _MUTABLE_COLUMNS))
            ),
        ).returning(*_TABLE.c, literal_column("xmax = 0").label("inserted"))

        row = (await self._session.execute(stmt)).mappings().one_or_none()
        if row is None:
            unchanged = await self._get_by_ref(podcast.ref)
            return unchanged, UpsertOutcome.UNCHANGED
        outcome = UpsertOutcome.CREATED if row["inserted"] else UpsertOutcome.UPDATED
        return _to_domain(row), outcome

    async def get(self, podcast_id: UUID) -> Podcast | None:
        row = (
            (await self._session.execute(select(_TABLE).where(_TABLE.c.id == podcast_id)))
            .mappings()
            .one_or_none()
        )
        return _to_domain(row) if row is not None else None

    async def list(self, filters: PodcastFilters, page: PageRequest) -> Page[Podcast]:
        conditions = _conditions(filters)
        total = await self._session.scalar(
            select(func.count()).select_from(_TABLE).where(*conditions)
        )
        stmt = _ordered(select(_TABLE).where(*conditions)).limit(page.page_size).offset(page.offset)
        rows = (await self._session.execute(stmt)).mappings().all()
        return Page(
            items=[_to_domain(row) for row in rows],
            total=total or 0,
            page=page.page,
            page_size=page.page_size,
        )

    async def stream_all(self) -> AsyncIterator[Podcast]:
        # Server-side cursor: memory stays flat no matter how large the catalog is.
        result = await self._session.stream(
            _ordered(select(_TABLE)).execution_options(yield_per=_STREAM_BATCH_SIZE)
        )
        async for row in result.mappings():
            yield _to_domain(row)

    async def _get_by_ref(self, ref: ExternalRef) -> Podcast:
        stmt = select(_TABLE).where(
            _TABLE.c.source == ref.source, _TABLE.c.external_id == ref.external_id
        )
        return _to_domain((await self._session.execute(stmt)).mappings().one())


def _conditions(filters: PodcastFilters) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if filters.query:
        pattern = f"%{_escape_like(filters.query)}%"
        conditions.append(
            or_(
                _TABLE.c.title.ilike(pattern, escape="\\"),
                _TABLE.c.author.ilike(pattern, escape="\\"),
            )
        )
    if filters.genre:
        conditions.append(_TABLE.c.genres.contains([filters.genre]))
    if filters.language:
        # "en" matches "en" and any regional variant such as "en-US".
        language = filters.language.lower()
        column = func.lower(_TABLE.c.language)
        conditions.append(or_(column == language, column.like(f"{_escape_like(language)}-%")))
    return [and_(*conditions)] if conditions else []


def _ordered(stmt: Select[Any]) -> Select[Any]:
    return stmt.order_by(_TABLE.c.title, _TABLE.c.id)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _to_row(podcast: Podcast) -> dict[str, Any]:
    return {
        "source": podcast.ref.source,
        "external_id": podcast.ref.external_id,
        "title": podcast.title,
        "author": podcast.author,
        "description": podcast.description,
        "language": podcast.language,
        "country": podcast.country,
        "genres": list(podcast.genres),
        "primary_genre": podcast.primary_genre,
        "feed_url": podcast.feed_url,
        "store_url": podcast.store_url,
        "cover_image_url": podcast.cover_image_url,
        "palette": podcast.palette.to_hex() if podcast.palette else None,
        "explicit": podcast.explicit,
        "episode_count": podcast.episode_count,
        "released_at": podcast.released_at,
    }


def _to_domain(row: RowMapping) -> Podcast:
    return Podcast(
        id=row["id"],
        ref=ExternalRef(source=row["source"], external_id=row["external_id"]),
        title=row["title"],
        author=row["author"],
        description=row["description"],
        language=row["language"],
        country=row["country"],
        genres=tuple(row["genres"]),
        primary_genre=row["primary_genre"],
        feed_url=row["feed_url"],
        store_url=row["store_url"],
        cover_image_url=row["cover_image_url"],
        palette=ColorPalette.from_hex(row["palette"]) if row["palette"] else None,
        explicit=row["explicit"],
        episode_count=row["episode_count"],
        released_at=row["released_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
