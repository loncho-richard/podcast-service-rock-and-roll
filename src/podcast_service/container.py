from dependency_injector import containers, providers

from podcast_service.config import Settings
from podcast_service.infrastructure.persistence.database import (
    DatabaseHealthProbe,
    create_engine,
    create_session_factory,
)
from podcast_service.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


class Container(containers.DeclarativeContainer):
    """Composition root: the only place where concrete implementations are chosen."""

    wiring_config = containers.WiringConfiguration(packages=["podcast_service.api.routers"])

    settings = providers.Singleton(Settings)

    # --- persistence ---
    engine = providers.Singleton(create_engine, database_url=settings.provided.database_url)
    session_factory = providers.Singleton(create_session_factory, engine=engine)
    unit_of_work = providers.Factory(SqlAlchemyUnitOfWork, session_factory=session_factory)
    database_health_probe = providers.Factory(DatabaseHealthProbe, engine=engine)
