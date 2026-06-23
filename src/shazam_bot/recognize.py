import asyncio
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

from shazamio import Shazam

FFMPEG_TIMEOUT = 120
FALLBACK_MIN_DURATION = 30.0
SEGMENT_DURATION = 15
FALLBACK_FRACS = (0.25, 0.5, 0.75)

_shazam = Shazam()


@dataclass
class Track:
    title: str
    artist: str
    shazam_url: str
    cover_url: str | None
    apple_url: str | None
    spotify_url: str | None
    ytmusic_url: str | None
    deezer_url: str | None


def _parse_providers(track_json: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    spotify_url = ytmusic_url = deezer_url = None
    hub = track_json.get('hub', {})
    for provider in hub.get('providers', []):
        caption = provider.get('caption', '')
        actions = provider.get('actions', [])
        uri = next((a.get('uri', '') for a in actions if a.get('uri')), '')
        if 'Spotify' in caption:
            if uri.startswith('spotify:search:'):
                q = quote(unquote(uri[len('spotify:search:'):]))
                spotify_url = f'https://open.spotify.com/search/{q}'
            elif uri.startswith('https://'):
                spotify_url = uri
        elif 'YouTube Music' in caption:
            if uri.startswith('https://'):
                ytmusic_url = uri
        elif 'Deezer' in caption:
            if uri.startswith('https://'):
                deezer_url = uri
            else:
                q = quote(f'{track_json.get("title", "")} {track_json.get("subtitle", "")}'.strip())
                deezer_url = f'https://www.deezer.com/search/{q}'
    return spotify_url, ytmusic_url, deezer_url


def _extract_apple_url(track_json: dict[str, Any]) -> str | None:
    hub = track_json.get('hub', {})
    for option in hub.get('options', []):
        for action in option.get('actions', []):
            m = re.search(r'(?:https?://)?music\.apple\.com[^#"\s]*', action.get('uri', ''))
            if m:
                raw = m.group(0)
                return raw if raw.startswith('https://') else 'https://' + raw
    return None


def _parse_track(track_json: dict[str, Any]) -> Track:
    spotify_url, ytmusic_url, deezer_url = _parse_providers(track_json)
    return Track(
        title=track_json.get('title', 'Unknown'),
        artist=track_json.get('subtitle', 'Unknown'),
        shazam_url=track_json.get('url', ''),
        cover_url=track_json.get('images', {}).get('coverart'),
        apple_url=_extract_apple_url(track_json),
        spotify_url=spotify_url,
        ytmusic_url=ytmusic_url,
        deezer_url=deezer_url,
    )


async def _convert_to_wav(input_path: Path, output_path: Path, ss: str | None = None, duration: int = 60) -> bool:
    cmd = ['ffmpeg', '-y']
    if ss is not None:
        cmd += ['-ss', ss]
    cmd += ['-i', str(input_path), '-ac', '1', '-ar', '16000', '-t', str(duration), str(output_path)]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=FFMPEG_TIMEOUT)
        return proc.returncode == 0
    except Exception:  # noqa: BLE001
        return False


async def _get_duration(input_path: Path) -> float | None:
    try:
        proc = await asyncio.create_subprocess_exec(
            'ffprobe',
            '-v', 'quiet',
            '-show_entries', 'format=duration',
            '-of', 'csv=p=0',
            str(input_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        return float(stdout.decode().strip())
    except Exception:  # noqa: BLE001
        return None


async def _recognize_wav(wav_path: Path) -> Track | None:
    try:
        # recognize_song uses the Python fingerprinting path which is more reliable
        # than the Rust shazamio_core path used by recognize()
        result: dict[str, Any] = await _shazam.recognize_song(wav_path)
        if result and 'track' in result:
            return _parse_track(result['track'])
    except Exception:  # noqa: BLE001,S110
        pass
    return None


async def recognize(input_path: Path) -> Track | None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        wav0 = tmp_dir / 'seg0.wav'
        if not await _convert_to_wav(input_path, wav0):
            return None

        track = await _recognize_wav(wav0)
        if track:
            return track

        duration = await _get_duration(input_path)
        if not duration or duration <= FALLBACK_MIN_DURATION:
            return None

        wavs = [tmp_dir / f'seg{i + 1}.wav' for i in range(len(FALLBACK_FRACS))]
        positions = [str(int(duration * f)) for f in FALLBACK_FRACS]
        converted = await asyncio.gather(*[
            _convert_to_wav(input_path, wav, ss=pos, duration=SEGMENT_DURATION)
            for wav, pos in zip(wavs, positions, strict=False)
        ])

        results = await asyncio.gather(*[
            _recognize_wav(wav)
            for wav, ok in zip(wavs, converted, strict=False)
            if ok
        ])
        return next((r for r in results if r is not None), None)
