from podcast_service.domain.shared.exceptions import DomainError


class SourceUnavailableError(DomainError):
    code = "source_unavailable"


class PodcastRejectedError(DomainError):
    """The source has the podcast, but it does not pass normalization (e.g. not rock)."""

    code = "podcast_rejected"
