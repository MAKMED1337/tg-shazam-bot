import asyncio
import logging
from pathlib import Path

DOWNLOAD_TIMEOUT = 300
MAX_FILESIZE = '50M'
EXPECTED_PRINT_LINES = 2

logger = logging.getLogger(__name__)


async def fetch_mp3(query_or_url: str, dest_dir: Path) -> tuple[Path, str] | None:
    """Download as MP3 into dest_dir.

    Accepts either a full https:// URL (used directly) or a search query
    (passed to yt-dlp as ytsearch1:<query>).
    Returns (mp3_path, youtube_url) or None on failure.
    """
    target = query_or_url if query_or_url.startswith('https://') else f'ytsearch1:{query_or_url}'
    command = (
        'yt-dlp',
        '-f',
        'bestaudio',
        '-x',
        '--audio-format',
        'mp3',
        '--no-playlist',
        '--max-filesize',
        MAX_FILESIZE,
        '--no-progress',
        '--quiet',
        '-o',
        str(dest_dir / '%(id)s.%(ext)s'),
        '--print',
        'webpage_url',
        '--print',
        'after_move:filepath',
        target,
    )
    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception:
        logger.exception('Failed to start MP3 download: command=%r', command)
        return None

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=DOWNLOAD_TIMEOUT)
    except TimeoutError:
        proc.kill()
        stdout, stderr = await proc.communicate()
        logger.exception(
            'MP3 download timed out after %ss: command=%r stdout=%r stderr=%r',
            DOWNLOAD_TIMEOUT,
            command,
            stdout.decode(errors='replace'),
            stderr.decode(errors='replace'),
        )
        return None

    stdout_text = stdout.decode(errors='replace')
    stderr_text = stderr.decode(errors='replace')
    if proc.returncode != 0:
        logger.error(
            'MP3 download failed: returncode=%s command=%r stdout=%r stderr=%r',
            proc.returncode,
            command,
            stdout_text,
            stderr_text,
        )
        return None

    lines = stdout_text.strip().splitlines()
    if len(lines) < EXPECTED_PRINT_LINES:
        logger.error(
            'MP3 download returned unexpected output: command=%r stdout=%r stderr=%r',
            command,
            stdout_text,
            stderr_text,
        )
        return None

    youtube_url = lines[0].strip()
    mp3_path = Path(lines[1].strip())

    if not mp3_path.exists() or mp3_path.stat().st_size == 0:  # noqa: ASYNC240
        logger.error(
            'MP3 output file is missing or empty: path=%s command=%r stdout=%r stderr=%r',
            mp3_path,
            command,
            stdout_text,
            stderr_text,
        )
        return None

    return mp3_path, youtube_url
