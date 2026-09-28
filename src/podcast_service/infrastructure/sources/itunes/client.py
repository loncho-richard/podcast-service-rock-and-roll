import logging
from collections.abc import Iterable, Sequence
from typing import Any

import httpx

from podcast_service.domain.ingestion import (
    PodcastSource,
    RawPodcastRecord,
    SourceBatch,
    SourceMode,
    SourceUnavailableError,
)
from podcast_service.infrastructure import RetryPolicy, get_with_retry, is_transient
from podcast_service.infrastructure.observability import ITUNES_FALLBACKS, record_upstream
from podcast_service.infrastructure.sources.itunes.fallback import ITunesSampleFallback
from podcast_service.infrastructure.sources.itunes.mapper import map_result, result_id

logger = logging.getLogger(__name__)


class ITunesPodcastSource(PodcastSource):
    """iTunes Search API (no key needed) with retries and an offline fallback sample."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        base_url: str,
        country: str,
        retry_policy: RetryPolicy,
        fallback: ITunesSampleFallback,
    ) -> None:
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._country = country
        self._retry_policy = retry_policy
        self._fallback = fallback

    async def search(self, terms: Sequence[str], limit: int) -> SourceBatch:
        """Search each term (`limit` results per term). A failing term is logged and
        skipped; only when every term fails do we serve the stored sample instead."""
        results: list[Any] = []
        failed_terms = 0
        for term in terms:
            params = {
                "term": term,
                "media": "podcast",
                "entity": "podcast",
                "limit": limit,
                "country": self._country,
            }
            try:
                results.extend(await self._get_results("/search", params))
            except (httpx.HTTPError, ValueError) as exc:
                failed_terms += 1
                record_upstream("itunes", succeeded=False)
                logger.warning("iTunes search for %r failed: %r", term, exc)
            else:
                record_upstream("itunes", succeeded=True)

        if terms and failed_terms == len(terms):
            ITUNES_FALLBACKS.labels("search").inc()
            logger.warning("iTunes is unavailable; serving the stored sample instead")
            return SourceBatch(
                _unique_records(self._fallback.search_results(limit)), SourceMode.FALLBACK
            )
        return SourceBatch(_unique_records(results), SourceMode.LIVE)

    async def lookup(self, external_id: str) -> RawPodcastRecord | None:
        params = {"id": external_id, "entity": "podcast", "country": self._country}
        try:
            results = await self._get_results("/lookup", params)
        except httpx.HTTPStatusError as exc:
            if not is_transient(exc):
                record_upstream("itunes", succeeded=True)
                return None  # iTunes answers 400 for ids it cannot parse
            # Still failing after retries (e.g. 429 rate limit, 5xx): the source is down.
            return self._lookup_fallback(external_id, exc)
        except (httpx.HTTPError, ValueError) as exc:
            return self._lookup_fallback(external_id, exc)
        record_upstream("itunes", succeeded=True)

        podcast = next(
            (item for item in results if isinstance(item, dict) and item.get("kind") == "podcast"),
            None,
        )
        return map_result(podcast) if podcast is not None else None

    def _lookup_fallback(self, external_id: str, exc: Exception) -> RawPodcastRecord:
        logger.warning("iTunes lookup for %s failed: %r", external_id, exc)
        record_upstream("itunes", succeeded=False)
        ITUNES_FALLBACKS.labels("lookup").inc()
        item = self._fallback.lookup_result(external_id)
        if item is None:
            raise SourceUnavailableError(
                "The podcast source is unavailable, please try again later."
            ) from exc
        return map_result(item)

    async def _get_results(self, path: str, params: dict[str, Any]) -> list[Any]:
        response = await get_with_retry(
            self._http, f"{self._base_url}{path}", self._retry_policy, params
        )
        payload: Any = response.json()
        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            raise ValueError(f"Unexpected iTunes payload from {path}")
        return results


def _unique_records(items: Iterable[Any]) -> list[RawPodcastRecord]:
    """The same show often matches several terms; keep one copy per iTunes id.

    Items without an id are kept so the normalizer reports them as skipped.
    """
    records: list[RawPodcastRecord] = []
    seen: set[str] = set()
    for item in items:
        external_id = result_id(item)
        if external_id is not None:
            if external_id in seen:
                continue
            seen.add(external_id)
        records.append(map_result(item))
    return records
