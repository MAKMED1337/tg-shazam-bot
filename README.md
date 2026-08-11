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

YouTube commonly blocks unauthenticated downloads from VPS/datacenter IPs. On a
computer with a browser where you are signed in to YouTube, close the browser
and run the cookie export helper. The browser name is required:

```sh
uv run scripts/export_youtube_cookies.py firefox
```

It accepts the same browser format as `yt-dlp`, including a profile, keyring, or
Firefox container. For example:

```sh
uv run scripts/export_youtube_cookies.py 'chrome:Default'
uv run scripts/export_youtube_cookies.py 'chromium+gnomekeyring:Profile 1'
```

Supported browsers are Brave, Chrome, Chromium, Edge, Firefox, Opera, Safari,
Vivaldi, and Whale. Run the script with `--help` for the full syntax. It creates
the Netscape-format cookie file expected by Docker at:

```text
.env/yt-dlp/youtube-cookies.txt
```

Keep this file private: it contains authenticated browser sessions. The helper
sets its permissions to `0600`, and the file is ignored by Git because the
entire `.env/` directory is ignored. Using a separate browser profile and
YouTube account is recommended. Copy the resulting file to the same path in the
project checkout on the VPS before starting Docker.

Then deploy or restart the bot:

```sh
docker compose up --build
```

Compose mounts the cookie directory read-only and sets `YT_DLP_COOKIES_FILE`.
If the VPS IP is still blocked, set an authenticated residential proxy in
`.env/bot.env` as `YT_DLP_PROXY=http://user:password@host:port`. Proxy values and
cookie paths are redacted from downloader command logs. Cookies expire, so
repeat the export if downloads start returning a YouTube sign-in challenge.

For a non-Docker deployment, set `YT_DLP_COOKIES_FILE` to the absolute path of
the exported file. Both authentication settings are optional for local IPs that
YouTube does not challenge.

## Useful tools

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — download audio/video from YouTube and 1000+ sites
- [songrec](https://github.com/marin-m/SongRec) — open-source Shazam client for Linux
- [shazamio](https://github.com/dotX12/ShazamIO) — async Python library for the Shazam API

## License

GPL-3.0-or-later
