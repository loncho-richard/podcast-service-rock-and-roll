from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AccessToken:
    token: str
    expires_in: int


class TokenService(ABC):
    @abstractmethod
    def issue(self, subject: str) -> AccessToken: ...

    @abstractmethod
    def verify(self, token: str) -> str:
        """Return the token's subject, or raise `AuthenticationError`."""
