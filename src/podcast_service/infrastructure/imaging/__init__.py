"""Cover download and color palette extraction."""

from podcast_service.infrastructure.imaging.http_image_fetcher import HttpImageFetcher
from podcast_service.infrastructure.imaging.pillow_palette_extractor import PillowPaletteExtractor

__all__ = [
    "HttpImageFetcher",
    "PillowPaletteExtractor",
]
