import asyncio
from request import get_all_play_info
from loggers import setup_logging_pre
import sys

try:
    setup_logging_pre()
    asyncio.run(get_all_play_info())
except KeyboardInterrupt:
    sys.exit(0)
