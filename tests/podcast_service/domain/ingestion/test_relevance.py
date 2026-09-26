import pytest

from podcast_service.domain.ingestion.relevance import RockRelevancePolicy


@pytest.mark.parametrize(
    ("title", "author", "genres"),
    [
        ("Classic Rock Hour", "Radio X", ("Music",)),
        ("The Rock'n'Roll Show", "Radio X", ("Music History",)),
        ("Rocknroll Stories", "Radio X", ("Music Commentary",)),
        ("Garage Tapes", "Punk Collective", ("Music",)),
        ("Heavy Metal Mondays", "Radio X", ("Music Interviews",)),
        ("Rockabilly Revival", "Radio X", ("Music",)),
        ("ClassicRockHistory.com", "Brian K", ("Music History",)),
        ("Hard Rocking Trivia Show", "Radio X", ("Music Commentary",)),
        ("Hårdrock - för fan", "Radio X", ("Music",)),
        ("Catch Me In The Pit", "PunkRock RonSwanson", ("Music",)),
    ],
)
def test_music_podcasts_with_rock_keywords_qualify(
    relevance: RockRelevancePolicy, title: str, author: str, genres: tuple[str, ...]
) -> None:
    assert relevance.is_rock_related(title=title, author=author, genres=genres)


@pytest.mark.parametrize(
    ("title", "author", "genres"),
    [
        ("Rock Climbing Weekly", "Outdoor Co", ("Sports", "Wilderness")),
        ("Punk Rock Therapy", "Josh J", ("Mental Health", "Health & Fitness")),
        ("Jazz Standards", "Blue Note Radio", ("Music",)),
        ("Rocket Science", "Radio X", ("Music",)),
        ("Metallurgy Today", "Radio X", ("Music",)),
        ("Classic Rock Hour", "Radio X", ()),
    ],
    ids=[
        "not-music",
        "rock-keyword-but-not-music",
        "no-keyword",
        "rocket-is-not-rock",
        "partial-word",
        "no-genres",
    ],
)
def test_other_podcasts_do_not_qualify(
    relevance: RockRelevancePolicy, title: str, author: str, genres: tuple[str, ...]
) -> None:
    assert not relevance.is_rock_related(title=title, author=author, genres=genres)
