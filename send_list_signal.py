import redis
import httpx
import json
import time
import zmq
from typing import List, Dict
from datetime import datetime
import logging
from loggers import setup_logging_pre
# asyncio.log.logger.setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

BYSET = "208ae30a-a4fe-42d4-9e51-e6fd1ad2a7a9" # base series 2
BYPLAYERS = "1629634"  # clarke
TARGET_PRICE = 17

# USER_ID = 'auth0|5ff10ff500625e0068d1855f'  # Crypto_Goya
USER_ID = 'auth0|5ff110779d0613006feebba4'  # multivac

url = "https://api.nba.dapperlabs.com/marketplace/graphql?SearchMintedMoments"

gql_dict = {
    "operationName": "SearchMintedMoments",
    "variables": {
        "sortBy": "ACQUIRED_AT_DESC", 
        "byOwnerDapperID": [USER_ID],
        "bySets": [BYSET],
        "bySeries": [], 
        "bySetVisuals": [], 
        "byPlayers": [BYPLAYERS],
        "byPlays": [], 
        "byTeams": [], 
        "byForSale": "NOT_FOR_SALE",
        "searchInput": {
            "pagination": {
                "cursor": "", 
                "direction": "RIGHT", 
                "limit": 50 
            }
        }
    },
    "query": open('graphql/SearchMintedMoments.graphql').read()
}

payload = json.dumps(gql_dict)

headers = {
    'Content-Type': 'application/json',
    'Cookie': '__cfduid=d068ddb63fc40817e27b55680431714031611305999'
}

def get_moments_id(res_json: Dict) -> List:
    search_filed = res_json['data']['searchMintedMoments']['data']['searchSummary']['data']['data']
    return list(map(lambda j: j['id'], filter(lambda i:  not i['forSale'], search_filed)))

def main():
    setup_logging_pre()
    r = redis.Redis(host='localhost', port=6379, db=0)
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind('tcp://*:6666')
    socket.send_string('hello')
    logger.info(f"send: hello")
    time.sleep(1)
    # send once
    response_json = httpx.post(url, data=payload, headers=headers).json()
    moments = get_moments_id(response_json)
    if len(moments) == 0:
        logger.info("要操作的moments为空")
    else:
        for moment in moments:
            signal = '1'+' '+moment+' '+str(TARGET_PRICE)
            if r.get(signal) is None:
                logger.info(f"send: {signal}")
                socket.send_string(signal)
                r.set(signal, 1)
            else:
                logger.info(f'{signal} has sent, skip')
            time.sleep(10)

main()
