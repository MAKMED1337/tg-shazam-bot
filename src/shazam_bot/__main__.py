import asyncio
import logging
import warnings

# pydub 0.25.1 contains non-raw regular expressions that Python 3.12 warns
# about while importing. They are valid regexes and do not affect execution.
warnings.filterwarnings('ignore', message='invalid escape sequence', category=SyntaxWarning)

from .bot import bot, dp  # noqa: E402


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
