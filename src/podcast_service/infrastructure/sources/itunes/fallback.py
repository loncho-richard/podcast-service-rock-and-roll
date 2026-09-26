import json
from functools import cached_property
from pathlib import Path
from typing import Any

from podcast_service.infrastructure.sources.itunes.mapper import result_id

DEFAULT_SAMPLE_PATH = Path(__file__).parent / "data" / "itunes_search_sample.json"


class ITunesSampleFallback:
    """Raw iTunes responses captured from the live API, served when it is unavailable.

    The sample always returns the same catalog regardless of the requested terms;
    it exists so ingestion keeps working offline, not to emulate search.
    """

    def __init__(self, path: Path = DEFAULT_SAMPLE_PATH) -> None:
        self._path = path

    def search_results(self, limit: int) -> list[Any]:
        return [
            item for response in self._responses for item in (response.get("results") or [])[:limit]
        ]

    def lookup_result(self, external_id: str) -> Any | None:
        return next(
            (
                item
                for response in self._responses
                for item in response.get("results") or []
                if result_id(item) == external_id
            ),
            None,
        )

    @cached_property
    def _responses(self) -> list[dict[str, Any]]:
        document = json.loads(self._path.read_text(encoding="utf-8"))
        return list(document["responses"].values())
