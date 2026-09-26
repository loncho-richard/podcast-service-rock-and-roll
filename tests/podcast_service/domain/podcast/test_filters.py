import pytest

from podcast_service.domain.podcast.filters import PageRequest


@pytest.mark.parametrize(
    ("page", "page_size", "expected_offset"),
    [(1, 20, 0), (2, 20, 20), (5, 10, 40)],
)
def test_page_request_offset(page: int, page_size: int, expected_offset: int) -> None:
    assert PageRequest(page, page_size).offset == expected_offset
