from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .recognize import Track


def build_caption(track: Track) -> str:
    return f'🎵 <b>{track.title}</b> — {track.artist}'


def build_keyboard(track: Track, youtube_url: str | None = None) -> InlineKeyboardMarkup:
    buttons: list[InlineKeyboardButton] = []
    if track.shazam_url:
        buttons.append(InlineKeyboardButton(text='🔍 Shazam', url=track.shazam_url))
    if track.apple_url:
        buttons.append(InlineKeyboardButton(text='🍎 Apple Music', url=track.apple_url))
    if track.spotify_url:
        buttons.append(InlineKeyboardButton(text='💚 Spotify', url=track.spotify_url))
    if track.ytmusic_url:
        buttons.append(InlineKeyboardButton(text='▶️ YT Music', url=track.ytmusic_url))
    if track.deezer_url:
        buttons.append(InlineKeyboardButton(text='🎧 Deezer', url=track.deezer_url))
    if youtube_url:
        buttons.append(InlineKeyboardButton(text='📺 YouTube', url=youtube_url))

    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=rows)
