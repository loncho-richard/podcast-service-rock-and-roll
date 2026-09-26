from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PodcastFilters:
    """`query` matches title or author (case-insensitive substring); the rest are exact."""

    query: str | None = None
    genre: str | None = None
    language: str | None = None


@dataclass(frozen=True, slots=True)
class PageRequest:
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


@dataclass(frozen=True, slots=True)
class Page[T]:
    items: list[T]
    total: int
    page: int
    page_size: int
