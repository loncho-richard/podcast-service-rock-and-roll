from podcast_service.domain.shared.exceptions import DomainError


class AuthenticationError(DomainError):
    code = "unauthorized"
