import logging
from io import BytesIO

from PIL import Image

from podcast_service.domain.ingestion.ports import PaletteExtractor
from podcast_service.domain.podcast.value_objects import ColorPalette, HexColor

logger = logging.getLogger(__name__)

_THUMBNAIL_SIZE = (150, 150)  # plenty for dominant colors, and fast to quantize


class PillowPaletteExtractor(PaletteExtractor):
    """Dominant colors via median-cut quantization, ordered by how much of the image
    each color covers."""

    def __init__(self, colors: int = 5, max_pixels: int = 40_000_000) -> None:
        self._colors = colors
        self._max_pixels = max_pixels  # guards against decompression bombs

    def extract(self, image: bytes) -> ColorPalette | None:
        try:
            with Image.open(BytesIO(image)) as source:
                if source.width * source.height > self._max_pixels:
                    logger.warning("Cover image too large: %sx%s", source.width, source.height)
                    return None
                source.draft("RGB", _THUMBNAIL_SIZE)  # cheap JPEG downscale while decoding
                rgb = source.convert("RGB")
            rgb.thumbnail(_THUMBNAIL_SIZE)
            quantized = rgb.quantize(colors=self._colors, method=Image.Quantize.MEDIANCUT)
            palette = quantized.getpalette() or []
            usage = sorted(quantized.getcolors() or [], reverse=True)  # (pixel count, index)
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            logger.warning("Could not extract a palette: %r", exc)
            return None

        colors: list[HexColor] = []
        for _, index in usage:
            if not isinstance(index, int):  # always an int for palette ("P") images
                continue
            red, green, blue = palette[index * 3 : index * 3 + 3]
            color = HexColor.from_rgb(red, green, blue)
            if color not in colors:
                colors.append(color)
        return ColorPalette(tuple(colors)) if colors else None
