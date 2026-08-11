import argparse
import copy
import stat
from http.cookiejar import Cookie
from pathlib import Path
from typing import Self

import pytest
from yt_dlp.cookies import YoutubeDLCookieJar

import scripts.export_youtube_cookies as exporter
from scripts.export_youtube_cookies import export_cookies, parse_browser_spec

_PRIVATE_FILE_MODE = 0o600


def test_parse_browser_spec_requires_supported_browser() -> None:
    with pytest.raises(argparse.ArgumentTypeError, match='unsupported browser'):
        parse_browser_spec('netscape')


def test_parse_browser_spec_accepts_browser() -> None:
    assert parse_browser_spec('firefox') == ('firefox', None, None, None)


def test_parse_browser_spec_accepts_keyring_and_profile() -> None:
    assert parse_browser_spec('chromium+gnomekeyring:Profile 1') == (
        'chromium',
        'Profile 1',
        'GNOMEKEYRING',
        None,
    )


def test_parse_browser_spec_accepts_firefox_container() -> None:
    assert parse_browser_spec('firefox:default::Personal') == ('firefox', 'default', None, 'Personal')


def test_export_cookies_writes_private_netscape_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cookie_jar = YoutubeDLCookieJar()
    cookie_jar.set_cookie(
        Cookie(
            version=0,
            name='SID',
            value='secret-value',
            port=None,
            port_specified=False,
            domain='.youtube.com',
            domain_specified=True,
            domain_initial_dot=True,
            path='/',
            path_specified=True,
            secure=True,
            expires=None,
            discard=False,
            comment=None,
            comment_url=None,
            rest={},
            rfc2109=False,
        ),
    )
    unrelated_cookie = copy.copy(next(iter(cookie_jar)))
    unrelated_cookie.domain = '.example.com'
    unrelated_cookie.name = 'PRIVATE'
    unrelated_cookie.value = 'unrelated-private-value'
    cookie_jar.set_cookie(unrelated_cookie)

    class FakeYoutubeDL:
        def __init__(self, _params: object) -> None:
            self.cookiejar = cookie_jar

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    monkeypatch.setattr(exporter, 'YoutubeDL', FakeYoutubeDL)
    output = tmp_path / 'private' / 'youtube-cookies.txt'

    assert export_cookies(('firefox', None, None, None), output) == 1
    assert output.read_text().startswith('# Netscape HTTP Cookie File')
    assert 'secret-value' in output.read_text()
    assert 'unrelated-private-value' not in output.read_text()
    assert stat.S_IMODE(output.stat().st_mode) == _PRIVATE_FILE_MODE
