import re
from dataclasses import dataclass

from podcast_service.domain.shared.exceptions import InvalidValueError

_HEX_COLOR = re.compile(r"^#[0-9a-f]{6}$")


@dataclass(frozen=True, slots=True)
class ExternalRef:
    """Identity of a podcast in its upstream source; the natural key used for idempotency."""

    source: str
    external_id: str

    def __post_init__(self) -> None:
        if not self.source.strip() or not self.external_id.strip():
            raise InvalidValueError("External reference needs a source and an external id.")


@dataclass(frozen=True, slots=True)
class HexColor:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not _HEX_COLOR.match(normalized):
            raise InvalidValueError(f"Invalid hex color: {self.value!r}.")
        object.__setattr__(self, "value", normalized)

    @classmethod
    def from_rgb(cls, red: int, green: int, blue: int) -> "HexColor":
        return cls(f"#{red:02x}{green:02x}{blue:02x}")


@dataclass(frozen=True, slots=True)
class ColorPalette:
    """Dominant colors of a cover image, most dominant first."""

    colors: tuple[HexColor, ...]

    def __post_init__(self) -> None:
        if not self.colors:
            raise InvalidValueError("A color palette needs at least one color.")

    @classmethod
    def from_hex(cls, values: list[str]) -> "ColorPalette":
        return cls(tuple(HexColor(value) for value in values))

    def to_hex(self) -> list[str]:
        return [color.value for color in self.colors]
