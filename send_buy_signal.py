import asyncio
import logging
import zmq
from typing import List, Tuple
import time
import redis
import random
import logging
from request import load_targets_config, get_new_list_default, get_moment_listings
from loggers import setup_logging_pre
import subprocess

logger = logging.getLogger(__name__)


def get_target_number(old_list, new_list=None, target_price: float = 1) -> List[Tuple[str, float, float]]:
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


async def process(set_id, play_id, sn_targets, floor_price, socket, redis_client):
    # TODO 改为绝对数值
    # TODO 设置价格过滤
    margin = 0.15  # 接受floor价贵20%的特殊编号
    discount = 0.15  # 比floor价低20%的无视编号直接秒

    moment_listings_new = await get_moment_listings(set_id, play_id)
    target_infos = get_target_number(
        moment_listings_new, target_price=floor_price * (1 + margin))
    if len(target_infos) != 0:
        for target_info in target_infos:  # 测试时加上[:1]
            number, target_price, market_price = target_info[0], target_info[1], target_info[2]

            if market_price > target_price * (1-(margin+discount)):
                if number not in sn_targets:  # 如果目标编号不是特殊编号
                    logger.debug(
                        f"其他编号：{number}，目标价{target_price:.0f}, 现价{market_price:.0f}, 跳过")
                    continue
            signal = '0'+' '+set_id+' '+play_id+' ' + number
            url = f"www.nbatopshot.com/listings/p2p/{set_id}+{play_id}?serialNumber={number}"
            subprocess.run("pbcopy", universal_newlines=True,
                           input=url)  # 复制到剪切板
            logger.info(
                f"{url}，目标价{target_price:.0f}, 现价{market_price:.0f}, 进入购买")
            if redis_client.get(signal) is None:
                logger.info(f"send: {signal}")
                socket.send_string(signal)
                redis_client.set(signal, 1)
            else:
                logger.info(f'{signal} has sent, skip')
    else:
        logger.debug("没有获取到目标价位的moment")


async def main():
    setup_logging_pre()
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind('tcp://*:6666')
    target_infos = await load_targets_config('./csv/35000.csv')  # 需要盯的名单设置在此处
    temp_moments = []
    while True:
        try:
            # 循环获取最近上新 和缓存对比
            # TODO default换成默认查询，否则太慢抢不到
            new_moments = await get_new_list_default()
            moments_will_search = []

            if len(temp_moments) == 0:
                moments_will_search = new_moments
            else:
                old_ids = list(map(lambda m: m['id'], temp_moments))
                new_ids = list(map(lambda m: m['id'], new_moments))
                last = old_ids[-1]
                if last in new_ids:
                    moments_will_search = new_moments[new_ids.index(last)+1:]
                else:
                    moments_will_search = new_moments

            if len(moments_will_search) == 0:
                logger.debug("没有新上架的瞬间")
            else:
                search_play_ids = list(
                    map(lambda i: i['play']['id'], moments_will_search))
                logger.debug(f"过滤查询的moment数量为: {len(moments_will_search)}")
                temp_moments = new_moments
                filter_target_infos = list(
                    filter(lambda s: s[1] in search_play_ids, target_infos))
                if len(filter_target_infos) != 0:
                    logger.info(
                        f"过滤查询在表格中的moment数量为: {len(filter_target_infos)}")
                    for buy_number_list in await asyncio.gather(*[process(target_info[0], target_info[1], target_info[2], target_info[3], socket, redis_client) for target_info in filter_target_infos]):
                        logger.debug(f"Buy list is {buy_number_list}")
                else:
                    logger.debug("最新上架没有表格中的")
        except Exception as e:
            logger.warning(f"send_buy_signal错误:{e}")
        finally:
            time.sleep(random.uniform(5, 7))

asyncio.run(main())
