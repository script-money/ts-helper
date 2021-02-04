import zmq
from worker import Worker
import threading
import queue
import os
from dotenv import load_dotenv

def check_account():
    account = os.getenv('DAPPER_ACCOUNT')
    password = os.getenv('DAPPER_PASSWORD')
    if (account is None) or (password is None):
        print('请在.env中填入账号密码')
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
           

def main():
    load_dotenv('.env')
    max_thread = 1 # 开几个selenium
    queue_size = 10
    queue_instance = queue.Queue(queue_size)

    context = zmq.Context()

    socket = context.socket(zmq.SUB)
    socket.connect('tcp://0.0.0.0:6666')
    socket.setsockopt_string(zmq.SUBSCRIBE, '')

    account, password = check_account()
    if account is None or password is None:
        # TODO 有概率出现报错
        return

    for t in range(max_thread):
        threading.Thread(target=worker, args=(
            t, account, password, queue_instance), daemon=True).start()

    while True:
        msg = socket.recv()
        print('\n')
        print(msg)
        try:
            queue_instance.put(msg, block=True, timeout=5)
        except queue.Full:
            print("队列已满,退出")
            # break


main()
