"""Integration tests for recognize().

Place audio files in tests/data/ and list them in tests/data/test_cases.json:

    [
      {
        "file": "song.mp3",
        "title": "Expected Title",
        "artist": "Expected Artist"
      }
    ]

Both the JSON and audio files are gitignored.
"""

import json
from pathlib import Path

import pytest

from shazam_bot.recognize import recognize

_DATA_DIR = Path(__file__).parent / 'data'
_CASES_FILE = _DATA_DIR / 'test_cases.json'


def _load_cases() -> list[dict[str, str]]:
    if not _CASES_FILE.exists():
        return []
    with _CASES_FILE.open() as f:
        return json.load(f)  # type: ignore[no-any-return]


def _case_id(case: dict[str, str]) -> str:
    return Path(case['file']).stem


@pytest.mark.parametrize('case', _load_cases(), ids=_case_id)
async def test_recognize(case: dict[str, str]) -> None:
    audio_path = Path(case['file'])
    if not audio_path.is_absolute():
        audio_path = _DATA_DIR / audio_path

    if not audio_path.exists():
        pytest.skip(f'{audio_path.name} not found in tests/data/')

    track = await recognize(audio_path)

    assert track is not None, f'Recognition returned None for {audio_path.name}'
    assert track.title.lower() == case['title'].lower(), (
        f'Title mismatch: got {track.title!r}, expected {case["title"]!r}'
    )
    assert track.artist.lower() == case['artist'].lower(), (
        f'Artist mismatch: got {track.artist!r}, expected {case["artist"]!r}'
    )
