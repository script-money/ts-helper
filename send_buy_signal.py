import asyncio
import logging
import zmq
from typing import List, Tuple
import time
import redis
import random
import logging
from utils import load_targets_config
from request import get_moment_listings
from loggers import setup_logging_pre

logger = logging.getLogger(__name__)

def get_target_number(old_list, new_list=None, target_price=1) -> List[Tuple[str, int, int]]: 
    if new_list is None:
        filter_by_price_single = filter(lambda n: float(
            n['moment']['price']) <= target_price, old_list)
        return list(map(lambda n: (n['moment']['flowSerialNumber'], target_price, int(float(n['moment']['price']))), filter_by_price_single))

    filter_listings = filter(
        lambda n: n['id'] not in map(lambda j: j['id'], old_list),
        new_list
    )
    filter_by_price = filter(lambda n: float(
        n['moment']['price']) <= target_price, filter_listings)
    return list(map(lambda n: (n['moment']['flowSerialNumber'], target_price, int(float(n['moment']['price']))), filter_by_price))


async def process(set_id, play_id, target_price, socket, redis_client):
    moment_listings_new = await get_moment_listings(set_id, play_id)
    target_infos = get_target_number(
        moment_listings_new, target_price=target_price)

    if len(target_infos) != 0:
        for target_info in target_infos:  # 测试时加上[:1]
            number, target_price, market_price = target_info[0], target_info[1], target_info[2]
            # 小于目标价20%的直接秒
            if market_price > target_price * (1-0.2):
                # 对序号进行筛选，小于500的就买
                low_number = 500
                if int(number) >= low_number:
                    logger.info(
                        f"号码是{number}，目标价{target_price}, 现价{market_price}, 跳过")
                    continue
                continue
            signal = '0'+' '+set_id+' '+play_id+' '+ n
            if redis_client.get(signal) is None:
                logger.info(f"send: {signal}")
                socket.send_string(signal)
                redis_client.set(signal, 1)
            else:
                logger.info(f'{signal} has sent, skip')
    else:
        logger.info("没有获取到目标价位的moment")

async def main():
    setup_logging_pre()
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind('tcp://*:6666')
    target_infos = load_targets_config('./csv/target.csv')
    print(target_infos)
    while True:
        try:
            for buy_number_list in await asyncio.gather(*[process(target_info[0], target_info[1], target_info[2], socket, redis_client) for target_info in target_infos]):
                logger.debug(f"Buy list is {buy_number_list}")
        except Exception as e:
            logger.warning(f"send_buy_signal错误:{e}")
        finally:
            time.sleep(random.uniform(7,12))

asyncio.run(main())
