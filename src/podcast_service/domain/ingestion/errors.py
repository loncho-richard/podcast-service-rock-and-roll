from podcast_service.domain.shared.exceptions import DomainError


class SourceUnavailableError(DomainError):
    code = "source_unavailable"
