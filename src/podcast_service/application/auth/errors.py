from podcast_service.domain.shared import DomainError


class AuthenticationError(DomainError):
    code = "unauthorized"
