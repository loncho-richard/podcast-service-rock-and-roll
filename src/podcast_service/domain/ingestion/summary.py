from dataclasses import dataclass
from enum import StrEnum


class SkipReason(StrEnum):
    MISSING_EXTERNAL_ID = "missing_external_id"
    MISSING_TITLE = "missing_title"
    MISSING_AUTHOR = "missing_author"
    NOT_ROCK_RELATED = "not_rock_related"
    DUPLICATE_IN_BATCH = "duplicate_in_batch"


class SourceMode(StrEnum):
    LIVE = "live"
    FALLBACK = "fallback"


@dataclass(frozen=True, slots=True)
class SkippedRecord:
    reason: SkipReason
    external_id: str | None = None
    title: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class IngestionSummary:
    source_mode: SourceMode
    fetched: int
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    palette_failures: int = 0
    skipped_records: tuple[SkippedRecord, ...] = ()

    @property
    def stored(self) -> int:
        return self.created + self.updated + self.unchanged

    @property
    def skipped(self) -> int:
        return len(self.skipped_records)
