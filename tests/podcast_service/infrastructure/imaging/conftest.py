from io import BytesIO

import httpx
import pytest
from PIL import Image

from podcast_service.infrastructure.imaging.http_image_fetcher import HttpImageFetcher
from podcast_service.infrastructure.imaging.pillow_palette_extractor import (
    PillowPaletteExtractor,
)
from podcast_service.infrastructure.resilience import RetryPolicy


def _encode(image: Image.Image, image_format: str) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format=image_format)
    return buffer.getvalue()


@pytest.fixture
def striped_png() -> bytes:
    """100x100 cover: 60% red, 30% green, 10% blue (vertical stripes)."""
    image = Image.new("RGB", (100, 100), (255, 0, 0))
    image.paste((0, 255, 0), (60, 0, 90, 100))
    image.paste((0, 0, 255), (90, 0, 100, 100))
    return _encode(image, "PNG")


@pytest.fixture
def transparent_png() -> bytes:
    return _encode(Image.new("RGBA", (20, 20), (255, 255, 255, 0)), "PNG")


@pytest.fixture
def palette_extractor() -> PillowPaletteExtractor:
    return PillowPaletteExtractor(colors=5)


@pytest.fixture
def small_limit_extractor() -> PillowPaletteExtractor:
    """Refuses anything above 50x50 pixels, to exercise the decompression-bomb guard."""
    return PillowPaletteExtractor(colors=5, max_pixels=2_500)


@pytest.fixture
def image_fetcher(http_client: httpx.AsyncClient, retry_policy: RetryPolicy) -> HttpImageFetcher:
    return HttpImageFetcher(http_client, retry_policy, max_bytes=1_000, deadline_seconds=0.2)
