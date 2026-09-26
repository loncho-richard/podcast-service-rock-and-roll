"""The podcast catalog: aggregate, value objects and repository port."""

from podcast_service.domain.podcast.entities import Podcast
from podcast_service.domain.podcast.filters import Page, PageRequest, PodcastFilters
from podcast_service.domain.podcast.repository import PodcastRepository, UpsertOutcome
from podcast_service.domain.podcast.value_objects import ColorPalette, ExternalRef, HexColor

__all__ = [
    "ColorPalette",
    "ExternalRef",
    "HexColor",
    "Page",
    "PageRequest",
    "Podcast",
    "PodcastFilters",
    "PodcastRepository",
    "UpsertOutcome",
]
