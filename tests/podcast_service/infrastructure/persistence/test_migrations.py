from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from podcast_service.infrastructure.persistence.models import Base


def _diff(connection: Connection) -> list[object]:
    return list(compare_metadata(MigrationContext.configure(connection), Base.metadata))


async def test_migrations_produce_exactly_the_mapped_schema(database: AsyncEngine) -> None:
    async with database.connect() as connection:
        assert await connection.run_sync(_diff) == []
