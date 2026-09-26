import pytest

from podcast_service.domain.podcast.value_objects import ColorPalette, ExternalRef, HexColor
from podcast_service.domain.shared.exceptions import InvalidValueError


def test_hex_color_is_normalized_to_lowercase() -> None:
    assert HexColor(" #A1B2C3 ").value == "#a1b2c3"


def test_hex_color_from_rgb() -> None:
    assert HexColor.from_rgb(255, 0, 16) == HexColor("#ff0010")


@pytest.mark.parametrize("value", ["", "#fff", "a1b2c3", "#gggggg", "#a1b2c3d4"])
def test_invalid_hex_colors_are_rejected(value: str) -> None:
    with pytest.raises(InvalidValueError):
        HexColor(value)


def test_palette_round_trips_hex_values() -> None:
    assert ColorPalette.from_hex(["#FF0000", "#00ff00"]).to_hex() == ["#ff0000", "#00ff00"]


def test_empty_palette_is_rejected() -> None:
    with pytest.raises(InvalidValueError):
        ColorPalette(())


@pytest.mark.parametrize(("source", "external_id"), [("", "1"), ("itunes", " ")])
def test_external_ref_requires_source_and_id(source: str, external_id: str) -> None:
    with pytest.raises(InvalidValueError):
        ExternalRef(source, external_id)
