import stat
from pathlib import Path

import pytest

from shazam_bot.download import _build_target, _redact_command, _yt_dlp_auth_args

_PRIVATE_FILE_MODE = 0o600


def test_build_target_converts_youtube_music_search_url() -> None:
    url = 'https://music.youtube.com/search?q=How+Much+Is+The+Fish%3F+Scooter&feature=shazam'

    assert _build_target(url) == 'ytsearch1:How Much Is The Fish? Scooter'


def test_build_target_keeps_youtube_watch_url() -> None:
    url = 'https://music.youtube.com/watch?v=teW0KULIir0'

    assert _build_target(url) == url


def test_build_target_converts_plain_query() -> None:
    assert _build_target('How Much Is The Fish? Scooter') == 'ytsearch1:How Much Is The Fish? Scooter'


def test_auth_args_include_readable_cookie_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cookies_file = tmp_path / 'cookies.txt'
    cookie_contents = '# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tSID\tsecret\n'
    cookies_file.write_text(cookie_contents)
    writable_dir = tmp_path / 'download'
    writable_dir.mkdir()
    monkeypatch.setenv('YT_DLP_COOKIES_FILE', str(cookies_file))
    monkeypatch.setenv('YT_DLP_PROXY', 'socks5://user:password@example.com:1080')

    assert _yt_dlp_auth_args(writable_dir) == (
        '--cookies',
        str(writable_dir / '.yt-dlp-cookies.txt'),
        '--proxy',
        'socks5://user:password@example.com:1080',
    )
    runtime_cookies_file = writable_dir / '.yt-dlp-cookies.txt'
    assert runtime_cookies_file.read_text() == cookie_contents
    assert cookies_file.read_text() == cookie_contents
    assert stat.S_IMODE(runtime_cookies_file.stat().st_mode) == _PRIVATE_FILE_MODE


def test_auth_args_ignore_missing_cookie_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv('YT_DLP_COOKIES_FILE', str(tmp_path / 'missing.txt'))
    monkeypatch.delenv('YT_DLP_PROXY', raising=False)

    assert _yt_dlp_auth_args() == ()


def test_redact_command_hides_auth_values() -> None:
    command = ('yt-dlp', '--cookies', '/secret/cookies.txt', '--proxy', 'http://user:pass@host', 'url')

    assert _redact_command(command) == (
        'yt-dlp',
        '--cookies',
        '<redacted>',
        '--proxy',
        '<redacted>',
        'url',
    )
