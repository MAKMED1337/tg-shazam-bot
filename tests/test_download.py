from shazam_bot.download import _build_target


def test_build_target_converts_youtube_music_search_url() -> None:
    url = 'https://music.youtube.com/search?q=How+Much+Is+The+Fish%3F+Scooter&feature=shazam'

    assert _build_target(url) == 'ytsearch1:How Much Is The Fish? Scooter'


def test_build_target_keeps_youtube_watch_url() -> None:
    url = 'https://music.youtube.com/watch?v=teW0KULIir0'

    assert _build_target(url) == url


def test_build_target_converts_plain_query() -> None:
    assert _build_target('How Much Is The Fish? Scooter') == 'ytsearch1:How Much Is The Fish? Scooter'
