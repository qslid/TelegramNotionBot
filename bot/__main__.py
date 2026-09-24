"""Allow `python -m bot` as an alias for `python -m bot.main`."""

from bot.main import main
import asyncio
import logging

logger = logging.getLogger("bot")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Interrupted.")
