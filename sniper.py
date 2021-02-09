from typing import List, Tuple
from pid import PidFile
from pid.base import PidFileAlreadyLockedError
import logging
from loggers import setup_logging_pre
import asyncio
from time import perf_counter
import httpx
from request import get_moment_listings, get_recent_transactions, get_new_list_default
import json
import redis
from send_buy_signal import get_moment_listings
from utils import compare_moments, calculate_reasonable_price
logger = logging.getLogger('sniper')

wait_seconds = 3


async def get_moments_info(id_pairs, http_client) -> List:
    return await get_moment_listings(id_pairs[0], id_pairs[1], http_client, wait_seconds)


async def get_newlist_loop(wait_seconds, redis_client, http_client):
    time_start = perf_counter()
    logger.info('get new list')
    new_moments = await get_new_list_default()
    temp_moments = redis_client.get('temp_moments')
    moments_will_search = compare_moments(temp_moments, new_moments)
    redis_client.set('temp_moments', new_moments)

    search_params = map(lambda i: (
        i['set']['id'], i['play']['id']), moments_will_search)

    async for id_pair in search_params:  # (setid, playid)
        setid, playid = id_pair[0], id_pair[1]
        recent_transactions, adjust_volume, circulation_count = await get_recent_transactions(setid, playid)
        # TODO search_marketplace_transactions -> reasonable price (通过最近的交易，平衡后的成交量，策略来计算)
        reasonable_price = calculate_reasonable_price(
            recent_transactions, adjust_volume)
        old_moment_listing = await read_moment_listing_from_db(playid, redis_client)
        # TODO 过滤moment_list: GetUserMomentListings -> new_list_pack
        current_moment_listing = await get_moments_info(id_pair, http_client)
        new_list_moment = get_new_list(
            old_moment_listing, current_moment_listing)
        # TODO 和价格进行计算
        if new_list_moment['price'] < reasonable_price * 0.95:
            # send signal
        else:
            logger.info('skip')
        # add record to database
        await save_moment_listing(playid, current_moment_listing, redis_client)

    time_stop = perf_counter()
    process_time = time_stop - time_start
    if process_time < wait_seconds:
        await asyncio.sleep(wait_seconds - process_time)


async def sniper(redis_client, http_client):
    while True:
        await asyncio.create_task(
            get_newlist_loop(wait_seconds, redis_client, http_client)
        )


async def main():
    try:
        setup_logging_pre()

        with PidFile('run.py.pid'):
            logger.error("run process is not running, python run.py first")
    except PidFileAlreadyLockedError:
        logger.debug(f'run process is running')
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        async with httpx.AsyncClient() as http_client:
            await sniper(redis_client, http_client)

asyncio.run(main())
