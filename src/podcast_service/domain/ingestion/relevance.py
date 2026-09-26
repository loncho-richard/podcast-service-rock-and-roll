import re
from collections.abc import Sequence

# "rock" may sit inside a compound ("HardRockCore", "ClassicRockHistory", "Hårdrock",
# "Rocking") but "rocket" is not rock; the other genres must be whole words.
_ROCK_KEYWORDS = re.compile(r"rock(?!et)|\b(?:punk|grunge|metal)\b", re.IGNORECASE)


class RockRelevancePolicy:
    """Decides what counts as a rock & roll podcast.

    A podcast qualifies when it is filed under a music genre (iTunes: "Music",
    "Music History", "Music Commentary", ...) AND a rock keyword appears in its
    title, author or genres. Requiring the music genre filters out false friends
    that iTunes happily returns for rock searches: "Punk Rock Therapy" (mental
    health), "Hard Rock Crochet" (crafts), "Rock and Roll it" (cricket).
    """

    def is_rock_related(self, *, title: str, author: str, genres: Sequence[str]) -> bool:
        is_music = any(genre.lower().startswith("music") for genre in genres)
        searchable = " ".join([title, author, *genres])
        return is_music and _ROCK_KEYWORDS.search(searchable) is not None
