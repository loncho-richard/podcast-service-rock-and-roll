class DomainError(Exception):
    """Base class for business-rule violations. `code` is exposed in API error bodies."""

    code: str = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    code = "not_found"
