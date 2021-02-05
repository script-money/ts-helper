import httpx
import asyncio,logging
import json
import zmq
from typing import List
import time
import redis
import random
import logging

logger = logging.getLogger(__name__)
asyncio.log.logger.setLevel(logging.ERROR)

SETID = "ad8e85a4-2240-4604-95f6-be826966d988" # cool cat
PLAYIDS = ["58f19b13-6b92-40e5-90d2-7e0de29be912", "6fa60eb1-d1c3-4d4c-952c-fde0136e4c83", "d690974d-5399-4775-b7ff-9f3c076f0719", "dc7e06d0-18d5-461d-a67d-127a06d885ca", "f1fc302c-376b-4206-8d18-b110fa5ed1e9"]
TARGET_PRICE = 140

# SETID = "208ae30a-a4fe-42d4-9e51-e6fd1ad2a7a9"  # base set 2
# PLAYIDS = ["d07c7e9a-8b73-42d6-ba69-1f128b1641eb"] # clark
# TARGET_PRICE = 5

url = "https://api.nba.dapperlabs.com/marketplace/graphql?GetUserMomentListings"

headers = {
    'Content-Type': 'application/json',
    'Cookie': '__cfduid=d068ddb63fc40817e27b55680431714031611305999'
}

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

async def process(play_id, client, socket, redis_client):
    gql_dict = {
        "operationName": "GetUserMomentListings",
        "variables": {
            "input": {
                "setID": SETID,
                "playID": play_id
            }
        },
        "query": open('graphql/GetUserMomentListings.graphql').read()
    }
    payload = json.dumps(gql_dict)
    try:
        r = await client.post(url, data=payload, headers=headers, timeout=7)
        response_json = r.json()
        moment_listings_new = response_json['data']['getUserMomentListings']['data']['momentListings']
        buy_number_list = get_target_number(
            moment_listings_new, target_price=TARGET_PRICE)
        if len(buy_number_list) != 0:
            for n in buy_number_list: # 测试时加上[:1]
                signal = '0'+' '+SETID+' '+play_id+' '+str(n)
                if redis_client.get(signal) is None:
                    logger.info(f"send: {signal}")
                    socket.send_string(signal)
                    redis_client.set(signal, 1)
                else:
                    logger.info(f'{signal} has sent, skip')
    except Exception as e:
        logger.warning(f"httpx request error: {e}")
        return []
    return buy_number_list

async def main():
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind('tcp://*:6666')

    # TODO 实现 send_load_signal 让浏览器先打开一遍追踪的文件，实现缓存。
    async with httpx.AsyncClient() as client:
        while True:
            for buy_number_list in await asyncio.gather(*[process(PLAYID, client, socket, redis_client) for PLAYID in PLAYIDS]):
                logger.debug(f"Buy list is {buy_number_list}")
            time.sleep(random.uniform(7,12))

asyncio.run(main())
