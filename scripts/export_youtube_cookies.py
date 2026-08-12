#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["yt-dlp[default]"]
# ///
"""Export browser cookies to the file mounted into the bot container."""

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.cookies import SUPPORTED_BROWSERS, SUPPORTED_KEYRINGS, YoutubeDLCookieJar

DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / '.env' / 'yt-dlp' / 'youtube-cookies.txt'
_BROWSER_SPEC_RE = re.compile(
    r"""(?x)
        (?P<name>[^+:]+)
        (?:\s*\+\s*(?P<keyring>[^:]+))?
        (?:\s*:\s*(?!:)(?P<profile>.+?))?
        (?:\s*::\s*(?P<container>.+))?
    """,
)


def parse_browser_spec(value: str) -> tuple[str, str | None, str | None, str | None]:
    """Parse yt-dlp's BROWSER[+KEYRING][:PROFILE][::CONTAINER] format."""
    match = _BROWSER_SPEC_RE.fullmatch(value)
    if match is None:
        msg = f'invalid browser specification: {value!r}'
        raise argparse.ArgumentTypeError(msg)

    browser, keyring, profile, container = match.group('name', 'keyring', 'profile', 'container')
    browser = browser.strip().lower()
    if browser not in SUPPORTED_BROWSERS:
        supported = ', '.join(sorted(SUPPORTED_BROWSERS))
        msg = f'unsupported browser {browser!r}; choose one of: {supported}'
        raise argparse.ArgumentTypeError(msg)

    if keyring is not None:
        keyring = keyring.strip().upper()
        if keyring not in SUPPORTED_KEYRINGS:
            supported = ', '.join(sorted(name.lower() for name in SUPPORTED_KEYRINGS))
            msg = f'unsupported keyring {keyring.lower()!r}; choose one of: {supported}'
            raise argparse.ArgumentTypeError(msg)

    return browser, profile, keyring, container


def export_cookies(
    browser_spec: tuple[str, str | None, str | None, str | None],
    output: Path,
) -> int:
    """Extract only YouTube cookies and atomically write a Netscape cookie jar."""
    output = output.expanduser().resolve()
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    with YoutubeDL({'cookiesfrombrowser': browser_spec, 'quiet': True}) as ydl:  # type: ignore[no-untyped-call]
        cookie_jar = ydl.cookiejar

    youtube_cookie_jar = YoutubeDLCookieJar()  # type: ignore[no-untyped-call]
    for cookie in cookie_jar:
        domain = cookie.domain.lstrip('.').lower()
        if domain == 'youtube.com' or domain.endswith('.youtube.com'):
            youtube_cookie_jar.set_cookie(cookie)

    youtube_cookie_count = len(youtube_cookie_jar)
    if youtube_cookie_count == 0:
        msg = 'the selected browser profile has no YouTube cookies; sign in to YouTube and try again'
        raise RuntimeError(msg)

    file_descriptor, temporary_name = tempfile.mkstemp(prefix='.youtube-cookies-', dir=output.parent)
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)
    try:
        youtube_cookie_jar.save(  # type: ignore[no-untyped-call]
            str(temporary_path),
            ignore_discard=True,
            ignore_expires=True,
        )
        temporary_path.chmod(0o600)
        temporary_path.replace(output)
    finally:
        temporary_path.unlink(missing_ok=True)

    return youtube_cookie_count


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Export browser cookies for authenticated yt-dlp downloads.',
        epilog=(
            'Browser format: BROWSER[+KEYRING][:PROFILE][::CONTAINER], as accepted by yt-dlp. '
            'Examples: firefox, chrome:Default, chromium+gnomekeyring:Profile 1'
        ),
    )
    parser.add_argument('browser', type=parse_browser_spec, help='browser/profile from which to extract cookies')
    parser.add_argument(
        '-o',
        '--output',
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f'output cookie file (default: {DEFAULT_OUTPUT})',
    )
    return parser


def main() -> int:
    parser = _parser()
    args = parser.parse_args()
    try:
        youtube_count = export_cookies(args.browser, args.output)
    except Exception as error:  # noqa: BLE001
        parser.exit(1, f'error: cookie export failed: {error}\n')

    output = args.output.expanduser().resolve()
    sys.stdout.write(f'Exported {youtube_count} YouTube cookies to {output}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
