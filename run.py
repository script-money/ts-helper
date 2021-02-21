import zmq
import sys
import logging
from worker import Worker
import threading
import queue
import os
from dotenv import load_dotenv
from loggers import setup_logging_pre
from pid.decorator import pidfile
from pid.base import PidFileAlreadyLockedError

logger = logging.getLogger('selenium_runner')

def check_account():
    account = os.getenv('DAPPER_ACCOUNT')
    password = os.getenv('DAPPER_PASSWORD')
    if (account is None) or (password is None):
        return None, None
    return account, password


def worker(_name, _account, _password, _queue):
    sub_worker = Worker(_name, _account, _password)
    sub_worker.launch()
    while True:
        if not sub_worker.is_busy and not _queue.empty():
            signal = _queue.get()
            op = str(signal, 'utf_8')
            parameters = op.split(' ')
            sub_worker.dispatcher(parameters[0], parameters[1:])

@pidfile()         
def main():
    return_code = 1
    try:
        load_dotenv('.env')
        max_thread = 2 # 开几个selenium
        queue_size = 100
        logger.info(
            f'selenium worker number is {max_thread}, task queue size is {queue_size}')
        queue_instance = queue.Queue(queue_size)

        context = zmq.Context()

        socket = context.socket(zmq.SUB)
        socket.connect('tcp://0.0.0.0:6666')
        socket.setsockopt_string(zmq.SUBSCRIBE, '')

        account, password = check_account()
        if account is None or password is None:
            logger.error('please set account and password in .env')
            raise SystemExit

        for t in range(max_thread):
            threading.Thread(target=worker, args=(
                t, account, password, queue_instance), daemon=True).start()

        while True:
            msg = socket.recv()
            logger.info(f"recieve message: {msg}")
            try:
                queue_instance.put(msg, block=True, timeout=5)
            except queue.Full:
                logger.warning('Task queue is full')                
    except KeyboardInterrupt:
        logger.info('SIGINT received, aborting ...')
        return_code = 0
    except SystemExit as e:
        return_code = e
    except Exception as exp:
        logger.exception(f"Fatal exception:{exp}")
    finally:
        sys.exit(return_code)

try:
    setup_logging_pre()
    main()
except PidFileAlreadyLockedError:
    logger.error("run.py is running already")
