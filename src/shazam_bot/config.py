import os
from pathlib import Path

from dotenv import load_dotenv

_env_file = Path(os.getenv('ENV_FILE', '.env/bot.env'))
if _env_file.exists():
    load_dotenv(_env_file)

BOT_TOKEN: str = os.environ.get('BOT_TOKEN', '')
if not BOT_TOKEN:
    raise RuntimeError('BOT_TOKEN is not set. Check your .env/bot.env file.')
