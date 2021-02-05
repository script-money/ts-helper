from pid import PidFile
from pid.base import PidFileAlreadyLockedError
import logging
from loggers import setup_logging_pre

logger = logging.getLogger('sniper')

setup_logging_pre()

try:
    with PidFile('run.py.pid'):
        logger.error("run process is not running")
except PidFileAlreadyLockedError:
    logger.debug(f'run process is running')
