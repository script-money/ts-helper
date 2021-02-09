import httpx
import asyncio,logging
import json
import zmq
from typing import List
import time
import redis
import random
import logging
from request import get_moment_listings

logger = logging.getLogger(__name__)
asyncio.log.logger.setLevel(logging.ERROR)

SETID = "ad8e85a4-2240-4604-95f6-be826966d988" # cool cat
PLAYIDS = ["58f19b13-6b92-40e5-90d2-7e0de29be912", "6fa60eb1-d1c3-4d4c-952c-fde0136e4c83", "d690974d-5399-4775-b7ff-9f3c076f0719", "dc7e06d0-18d5-461d-a67d-127a06d885ca", "f1fc302c-376b-4206-8d18-b110fa5ed1e9"]
TARGET_PRICE = 140

# SETID = "208ae30a-a4fe-42d4-9e51-e6fd1ad2a7a9"  # base set 2
# PLAYIDS = ["d07c7e9a-8b73-42d6-ba69-1f128b1641eb"] # clark
# TARGET_PRICE = 5

def get_target_number(old_list, new_list=None, target_price=1) -> List:
    if new_list is None:
        filter_by_price_single = filter(lambda n: float(
            n['moment']['price']) <= target_price, old_list)
        return list(map(lambda n: n['moment']['flowSerialNumber'], filter_by_price_single))

    filter_listings = filter(
        lambda n: n['id'] not in map(lambda j: j['id'], old_list),
        new_list
    )
    filter_by_price = filter(lambda n: float(
        n['moment']['price']) <= target_price, filter_listings)
    return list(map(lambda n: n['moment']['flowSerialNumber'], filter_by_price))



# TODO 解藕为多个步骤
async def process(set_id, play_id, socket, redis_client):
    moment_listings_new = await get_moment_listings(set_id, play_id)
    buy_number_list = get_target_number(
        moment_listings_new, target_price=TARGET_PRICE)
    if len(buy_number_list) != 0:
        for n in buy_number_list: # 测试时加上[:1]
            signal = '0'+' '+set_id+' '+play_id+' '+str(n)
            if redis_client.get(signal) is None:
                logger.info(f"send: {signal}")
                socket.send_string(signal)
                redis_client.set(signal, 1)
            else:
                logger.info(f'{signal} has sent, skip')

async def main():
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind('tcp://*:6666')

    # TODO 实现 send_load_signal 让浏览器先打开一遍追踪的文件，实现缓存。
    while True:
        for buy_number_list in await asyncio.gather(*[process(SETID, PLAYID, socket, redis_client) for PLAYID in PLAYIDS]):
            logger.debug(f"Buy list is {buy_number_list}")
        time.sleep(random.uniform(7,12))

asyncio.run(main())
