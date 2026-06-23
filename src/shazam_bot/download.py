import asyncio
from pathlib import Path

DOWNLOAD_TIMEOUT = 300
MAX_FILESIZE = '50M'
EXPECTED_PRINT_LINES = 2


async def fetch_mp3(query_or_url: str, dest_dir: Path) -> tuple[Path, str] | None:
    """Download as MP3 into dest_dir.

    Accepts either a full https:// URL (used directly) or a search query
    (passed to yt-dlp as ytsearch1:<query>).
    Returns (mp3_path, youtube_url) or None on failure.
    """
    target = query_or_url if query_or_url.startswith('https://') else f'ytsearch1:{query_or_url}'
    proc = await asyncio.create_subprocess_exec(
        'yt-dlp',
        '-f', 'bestaudio',
        '-x',
        '--audio-format', 'mp3',
        '--no-playlist',
        '--max-filesize', MAX_FILESIZE,
        '--no-progress',
        '--quiet',
        '-o', str(dest_dir / '%(id)s.%(ext)s'),
        '--print', 'webpage_url',
        '--print', 'after_move:filepath',
        target,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=DOWNLOAD_TIMEOUT)
    except TimeoutError:
        proc.kill()
        return None

    if proc.returncode != 0:
        return None

    lines = stdout.decode().strip().splitlines()
    if len(lines) < EXPECTED_PRINT_LINES:
        return None

    youtube_url = lines[0].strip()
    mp3_path = Path(lines[1].strip())

    if not mp3_path.exists() or mp3_path.stat().st_size == 0:  # noqa: ASYNC240
        return None

    return mp3_path, youtube_url
