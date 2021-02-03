import zmq
import random
import time
import redis

def main():
    r = redis.Redis(host='localhost', port=6379, db=0)
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind('tcp://*:6666')
    socket.send_string('hello')
    print(f"send: hello")
    time.sleep(1)
    # send recursive
    while True:
        signal = str(random.randint(0, 10))
        if r.get(signal) is None:
            print(f"send: {signal}")
            socket.send_string(signal)
            # docker exec -it redis redis-cli FLUSHALL && python send_buy_signal.py
            # docker run -p 6379:6379 --name redis redis
            r.set(signal, 1)
        else:
            print(f'{signal} has sent, skip')
        time.sleep(1)

if __name__ == "__main__":
    main()