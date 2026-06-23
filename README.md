> **This project was entirely vibecoded. No human thought went into it.**

# shazam-bot

Source code for [@shazam_music_searcher_bot](https://t.me/shazam_music_searcher_bot). Recognizes music in audio/video clips and replies with streaming links and an MP3 of the full track.

## How it works

1. Send an audio clip, voice message, video, or audio document
2. The bot converts it to mono 16 kHz PCM and feeds it to **shazamio** (Shazam API client)
3. On a match it builds an inline keyboard with Shazam / Apple Music / Spotify / YT Music / Deezer / YouTube links
4. It then downloads the full track from YouTube via **yt-dlp** and sends the MP3

> **Limit:** Telegram's Bot API caps file downloads at 20 MB. Send a shorter clip if the file is larger.

## Local development

```sh
cp .env/bot.env.example .env/bot.env  # fill in BOT_TOKEN
uv sync
uv run python -m shazam_bot
```

Dependencies: `yt-dlp`, `ffmpeg` must be on `PATH`.

## Docker

```sh
docker compose up --build
```

The first build compiles songrec from source (Rust) — takes a few minutes; subsequent builds use the Docker layer cache.

## Useful tools

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — download audio/video from YouTube and 1000+ sites
- [songrec](https://github.com/marin-m/SongRec) — open-source Shazam client for Linux
- [shazamio](https://github.com/dotX12/ShazamIO) — async Python library for the Shazam API

## License

GPL-3.0-or-later
