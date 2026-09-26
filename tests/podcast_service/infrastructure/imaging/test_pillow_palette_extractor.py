import pytest

from podcast_service.domain.podcast.value_objects import ColorPalette
from podcast_service.infrastructure.imaging.pillow_palette_extractor import (
    PillowPaletteExtractor,
)


def test_palette_is_ordered_by_dominance(
    palette_extractor: PillowPaletteExtractor, striped_png: bytes
) -> None:
    assert palette_extractor.extract(striped_png) == ColorPalette.from_hex(
        ["#ff0000", "#00ff00", "#0000ff"]
    )


def test_images_with_alpha_are_supported(
    palette_extractor: PillowPaletteExtractor, transparent_png: bytes
) -> None:
    assert palette_extractor.extract(transparent_png) is not None


@pytest.mark.parametrize(
    "payload",
    [b"", b"definitely not an image", b"\x89PNG\r\n\x1a\n truncated"],
    ids=["empty", "text", "truncated-png"],
)
def test_undecodable_bytes_give_no_palette(
    palette_extractor: PillowPaletteExtractor, payload: bytes
) -> None:
    assert palette_extractor.extract(payload) is None


def test_oversized_images_are_refused(
    small_limit_extractor: PillowPaletteExtractor, striped_png: bytes
) -> None:
    assert small_limit_extractor.extract(striped_png) is None
