import re
from collections.abc import Sequence

_ROCK_KEYWORDS = re.compile(
    r"\b(?:rock|rock-?n-?roll|rockabilly|punk|grunge|metal)\b",
    re.IGNORECASE,
)


class RockRelevancePolicy:
    """Decides what counts as a rock & roll podcast.

    A podcast qualifies when it is filed under a music genre (iTunes: "Music",
    "Music History", "Music Commentary", ...) AND a rock keyword appears as a whole
    word in its title, author or genres. Requiring the music genre filters out
    false friends such as rock-climbing or geology shows.
    """

    def is_rock_related(self, *, title: str, author: str, genres: Sequence[str]) -> bool:
        is_music = any(genre.lower().startswith("music") for genre in genres)
        searchable = " ".join([title, author, *genres])
        return is_music and _ROCK_KEYWORDS.search(searchable) is not None
