import asyncio
from request import get_all_play_info
from loggers import setup_logging_pre
from analysis import generate_csv
import sys

async def main():
    await get_all_play_info()
    await generate_csv()

try:
    setup_logging_pre()
    asyncio.run(main())
except KeyboardInterrupt:
    sys.exit(0)
