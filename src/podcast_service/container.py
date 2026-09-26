from dependency_injector import containers, providers

from podcast_service.config import Settings


class Container(containers.DeclarativeContainer):
    """Composition root: the only place where concrete implementations are chosen."""

    wiring_config = containers.WiringConfiguration(packages=["podcast_service.api.routers"])

    settings = providers.Singleton(Settings)
