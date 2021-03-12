import asyncio
import logging
import zmq
from typing import List, Tuple
import time
import redis
import random
import logging
from request import load_targets_config
from request import get_moment_listings
from loggers import setup_logging_pre
import pandas as pd

logger = logging.getLogger(__name__)

def get_target_number(old_list, new_list=None, target_price:float=1) -> List[Tuple[str, float, float]]: 
    if new_list is None:
        filter_by_price_single = filter(lambda n: float(
            n['moment']['price']) <= target_price, old_list)
        return list(map(lambda n: (n['moment']['flowSerialNumber'], target_price, float(n['moment']['price'])), filter_by_price_single))

    filter_listings = filter(
        lambda n: n['id'] not in map(lambda j: j['id'], old_list),
        new_list
    )
    filter_by_price = filter(lambda n: float(
        n['moment']['price']) <= target_price, filter_listings)
    return list(map(lambda n: (n['moment']['flowSerialNumber'], target_price, float(n['moment']['price'])), filter_by_price))


async def process(set_id, play_id, total_le, floor_price, socket, redis_client):
    number_percentage = 1/10 # 前1/10视为小编号
    margin = 0.05 # 接受floor价贵5%的小编号
    discount = 0.15 # 比floor价低15%的无视编号直接秒

    moment_listings_new = await get_moment_listings(set_id, play_id)
    target_infos = get_target_number(
        moment_listings_new, target_price=floor_price * (1 + margin)) 
    if len(target_infos) != 0:
        for target_info in target_infos:  # 测试时加上[:1]
            number, target_price, market_price = target_info[0], target_info[1], target_info[2]
            
            if market_price > target_price * (1-(margin+discount)):
                low_number = total_le * number_percentage
                if int(number) >= low_number: # 如果是大编号
                    logger.info(
                        f"大编号：{number}，目标价{target_price:.0f}, 现价{market_price:.0f}, 跳过")
                    continue
                elif market_price > target_price:
                    logger.info(
                        f"小编号太贵：{number}，目标价{target_price:.0f}, 现价{market_price:.0f}, 跳过")
                    continue
            signal = '0'+' '+set_id+' '+play_id+' ' + number
            url = f"https://www.nbatopshot.com/listings/p2p/{set_id}+{play_id}?serialNumber={number}"
            pd.Series([url]).to_clipboard(index=False) # 复制网址到剪切板
            logger.info(
                f"{set_id}-{play_id}的{number}，目标价{target_price:.0f}, 现价{market_price:.0f}, 进入购买")
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
    target_infos = await load_targets_config('./csv/ss.csv') # 需要盯的名单设置在此处
    while True:
        try:
            for buy_number_list in await asyncio.gather(*[process(target_info[0], target_info[1], target_info[2], target_info[3], socket, redis_client) for target_info in target_infos]):
                logger.debug(f"Buy list is {buy_number_list}")
        except Exception as e:
            logger.warning(f"send_buy_signal错误:{e}")
        finally:
            time.sleep(random.uniform(3,8))

asyncio.run(main())
