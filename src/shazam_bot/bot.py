import asyncio
import contextlib
import logging
import tempfile
from pathlib import Path

import aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
from aiogram.types import FSInputFile

from .config import BOT_TOKEN
from .download import fetch_mp3
from .formatting import build_caption, build_keyboard
from .recognize import recognize

logger = logging.getLogger(__name__)

# AiohttpSession.timeout must be a plain float (seconds); aiogram adds it to
# polling_timeout internally. 600 s gives slow VPS connections time to upload large files.
bot = Bot(token=BOT_TOKEN, session=AiohttpSession(timeout=600))
dp = Dispatcher()

MAX_FILE_SIZE = 20 * 1024 * 1024  # Bot API hard limit
HTTP_OK = 200

HELP_TEXT = (
    'Send me an audio clip, voice message, video, or document with music '
    "and I'll identify the song and send you links + the MP3. 🎵"
)

_http_session: aiohttp.ClientSession | None = None


@dp.startup()
async def _on_startup() -> None:
    global _http_session  # noqa: PLW0603
    _http_session = aiohttp.ClientSession()


@dp.shutdown()
async def _on_shutdown() -> None:
    if _http_session and not _http_session.closed:
        await _http_session.close()


async def _download_cover(url: str, dest: Path) -> bool:
    if not _http_session:
        return False
    with contextlib.suppress(Exception):
        async with _http_session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == HTTP_OK:
                dest.write_bytes(await resp.read())  # noqa: ASYNC240
                return True
    return False


def _extract_media(message: types.Message) -> tuple[str, int | None, str] | None:
    if a := message.audio:
        return a.file_id, a.file_size, (a.mime_type or 'audio/mpeg').split('/')[-1] or 'mp3'
    if v := message.voice:
        return v.file_id, v.file_size, 'ogg'
    if v := message.video:
        return v.file_id, v.file_size, (v.mime_type or 'video/mp4').split('/')[-1] or 'mp4'
    if vn := message.video_note:
        return vn.file_id, vn.file_size, 'mp4'
    if (d := message.document) and (d.mime_type or '').startswith(('audio/', 'video/')):
        return d.file_id, d.file_size, (d.mime_type or '').split('/')[-1] or 'bin'
    return None


async def _handle_media(  # noqa: C901
    message: types.Message,
    file_id: str,
    file_size: int | None,
    file_ext: str,
) -> None:
    if file_size and file_size > MAX_FILE_SIZE:
        await message.reply('⚠️ File is too large (max 20 MB). Please send a shorter clip.')
        return

    logger.info('Recognition started: file_id=%s size=%s ext=%s', file_id, file_size, file_ext)
    status = await message.reply('🎧 Recognizing…')

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        input_path = tmp_dir / f'input.{file_ext}'

        try:
            await bot.download(file_id, destination=input_path)
        except Exception:
            logger.exception('TG download failed')
            with contextlib.suppress(Exception):
                await status.edit_text('⚠️ Failed to download the file. Please try again.')
            return

        track = await recognize(input_path)
        if track is None:
            logger.info('Recognition failed for file_id=%s', file_id)
            await status.edit_text("😔 Couldn't recognize the music.")
            return

        logger.info('Recognized: %s - %s', track.title, track.artist)

        # Kick off MP3 fetch immediately; download cover concurrently while it runs
        yt_source = track.ytmusic_url or f'{track.title} {track.artist}'
        mp3_task = asyncio.create_task(fetch_mp3(yt_source, tmp_dir))

        cover_path: Path | None = None
        if track.cover_url:
            cover_path = tmp_dir / 'cover.jpg'
            if not await _download_cover(track.cover_url, cover_path):
                cover_path = None

        # Send links as soon as cover is ready — don't wait for the MP3
        caption = build_caption(track)
        keyboard = build_keyboard(track)

        with contextlib.suppress(Exception):
            await status.delete()

        try:
            if cover_path:
                await message.reply_photo(
                    photo=FSInputFile(cover_path),
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode='HTML',
                )
            else:
                await message.reply(caption, reply_markup=keyboard, parse_mode='HTML')
        except Exception:
            logger.exception('Failed to send track info')

        mp3_result = await mp3_task
        logger.info('MP3 fetch %s for: %s - %s', 'succeeded' if mp3_result else 'failed', track.title, track.artist)

        if mp3_result:
            mp3_path, _ = mp3_result
            if mp3_path.exists():
                try:
                    await message.reply_audio(
                        audio=FSInputFile(mp3_path),
                        title=track.title,
                        performer=track.artist,
                        thumbnail=FSInputFile(cover_path) if cover_path else None,
                    )
                except Exception:
                    logger.exception('Failed to send MP3')
                    await message.reply('⚠️ The track was found, but the MP3 could not be sent. Please try again later.')
        else:
            await message.reply('⚠️ The track was found, but the MP3 could not be downloaded. Please try again later.')


@dp.message(Command('start', 'help'))
async def cmd_start(message: types.Message) -> None:
    await message.reply(f'👋 Hi! {HELP_TEXT}')


@dp.message(F.audio | F.voice | F.video | F.video_note | F.document)
async def handle_media(message: types.Message) -> None:
    media = _extract_media(message)
    if media is None:
        return
    await _handle_media(message, *media)
