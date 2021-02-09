import httpx
import logging
from typing import List, Tuple, Dict
from exceptions import HttpxRequestException
from utils import calculate_adjust_volume
import json
import asyncio
from itertools import groupby
from statistics import mean
import pandas as pd
from datetime import datetime
from time import perf_counter

asyncio.log.logger.setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

headers = {
    'Content-Type': 'application/json',
    'Cookie': '__cfduid=d068ddb63fc40817e27b55680431714031611305999'
}

base_market_url = "https://api.nba.dapperlabs.com/marketplace/graphql?"


async def get_new_list_default() -> List:
    """
    获取最新上架的12个moments

    Raises
    ------
    HttpxRequestException

    Return
    ------
    类型为 MomentListing 的列表

    """
    payload = {
        "operationName": "SearchMomentListingsDefault",
        "variables": {
            "byPlayers": [],
            "byTagNames": [],
            "byTeams": [],
            "bySets": [],
            "bySeries": [],
            "bySetVisuals": [],
            "byGameDate": {
                "start": None,
                "end": None
            },
            "byCreatedAt": {
                "start": None,
                "end": None
            },
            "byPower": {
                "min": None,
                "max": None
            },
            "byPrice": {
                "min": None,
                "max": None
            },
            "byListingType": [
                "BY_USERS"
            ],
            "byPlayStyle": [],
            "bySkill": [],
            "byPrimaryPlayerPosition": [],
            "bySerialNumber": {
                "min": None,
                "max": None
            },
            "searchInput": {
                "pagination": {
                    "cursor": "",
                    "direction": "RIGHT",
                    "limit": 12
                }
            },
            "orderBy": "UPDATED_AT_DESC"
        },
        "query": open('graphql/SearchMomentListingsDefault.graphql').read()
    }
    url = base_market_url+"SearchMomentListingsDefault="
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, data=json.dumps(payload), headers=headers)
            response_json = r.json()
            return response_json['data']['searchMomentListings']['data']['searchSummary']['data']['data']
    except Exception as e:
        logger.warning(f"httpx request error: {e}")
        raise HttpxRequestException


async def get_moment_listings(set_id, play_id) -> List:
    """
    获取某个play的上架信息，用于获取序号和列表
    
    Parameters
    ----------
    set_id: 包的id
    play_id: 动作的id

    Raises
    ------
    HttpxRequestException

    Return
    ------
    类型为 UserMomentListing 的列表

    """
    url = base_market_url + "GetUserMomentListings"
    payload = {
        "operationName": "GetUserMomentListings",
        "variables": {
            "input": {
                "setID": set_id,
                "playID": play_id
            }
        },
        "query": open('graphql/SearchMomentListingsDefault.graphql').read()
    }
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, data=json.dumps(payload), headers=headers)
            response_json = r.json()
            return response_json['data']['getUserMomentListings']['data']['momentListings']
    except Exception as e:
        logger.warning(f"httpx request error: {e}")
        raise HttpxRequestException


async def get_transactions(set_id, play_id, by_highest=False) -> Tuple[List[Tuple[int, float]], float, int, str, int]:
    """
    获取50条交易信息，返回辅助判断交易的参数

    Parameters
    ----------
    set_id: 包的id
    play_id: 动作的id
    by_highest: 如果为True, 按成交价返回，否则按最近交易时间返回

    Raises
    ------
    HttpxRequestException

    Return
    ------
    (recent_transactions, adjust_volume, circulation_count, jerseyNumber)
        recent_transactions: (序号,价格)的列表。类型为 List[Tuple[int, float]],  
        adjust_volume: 日成交量, 8位小数
        circulation_count: 该play的总供应量
        player: 球员名
        jersey_number: 球衣号
    """
    payload = {
        "operationName": "SearchMarketplaceTransactions",
        "variables": {
            "input": {
                "sortBy": "PRICE_DESC" if by_highest else "UPDATED_AT_DESC",
                "searchInput": {
                    "pagination": {
                        "cursor": "",
                        "direction": "RIGHT",
                        "limit": 50
                    }
                },
                "filters": {
                    "byEditions": [
                        {
                            "setID": set_id,
                            "playID": play_id
                        }
                    ]
                }
            }
        },
        "query": open('graphql/SearchMarketplaceTransactions.graphql').read()
    }
    url = base_market_url + "SearchMarketplaceTransactions"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                url,
                data=json.dumps(payload),
                headers=headers
            )
            response_json = r.json()
            
            marketplace_transactions = response_json['data']['searchMarketplaceTransactions']['data']['searchSummary']['data']['data']
            if len(marketplace_transactions) == 0:
                return [],0,0,'',-1
            recent_transactions = list(map(lambda i: (int(i['moment']['flowSerialNumber']), float(i['price'])), marketplace_transactions))
            adjust_volume = 0
            if not by_highest: # 用最近成交的排序来计算成交量
                adjust_volume = calculate_adjust_volume(
                    list(map(lambda i: i['updatedAt'], marketplace_transactions)))
            first_moment = marketplace_transactions[0]['moment']
            circulation_count = int(
                first_moment['setPlay']['circulationCount'])
            player = first_moment['play']['stats']['playerName']
            jersey_number = int(first_moment['play']['stats']['jerseyNumber'])
            return recent_transactions, adjust_volume, circulation_count, player, jersey_number
    except Exception as e:
        logger.warning(f"httpx request error: {e}")
        raise HttpxRequestException

async def get_codex() -> List[str]:
    """
    获取所有包的ID

    Raises
    ------
    HttpxRequestException

    Return
    ------
    各包的 id 列表   
    """
    url = base_market_url + "GetCodex="
    payload = {
        "operationName": "GetCodex",
        "variables": {
            "input": {
            }
        },
        "query": open('graphql/GetCodex.graphql').read()
    } 
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, data=json.dumps(payload), headers=headers)
            response_json = r.json()
            set_ids = response_json['data']['getCodex']['codex']
            return list(map(lambda s: s['set']['id'], set_ids))
    except Exception as e:
        logger.warning(f"httpx request error: {e}")
        raise HttpxRequestException


async def get_codex_set(set_id: str) -> List[Tuple[str,str]]:
    """
    获取特定Set下所有moment

    Parameters
    ----------
    set_id: 包的id

    Raises
    ------
    HttpxRequestException

    Return
    ------
    (set_id, play_id) 的列表
    """
    url = base_market_url + "GetCodexSet="
    payload = {
        "operationName": "GetCodexSet",
        "variables": {
            "input": {
                "setID": set_id
            }
        },
        "query": open('graphql/GetCodexSet.graphql').read()
        }
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, data=json.dumps(payload), headers=headers)
            response_json = r.json()
            edition_slots = response_json['data']['getCodexSet']['codexSetWithEditions']['editionSlots']
            return list(map(lambda e: (e['edition']['set']['id'], e['edition']['play']['id']), edition_slots))
    except Exception as e:
        logger.warning(f"httpx request error: {e}")
        raise HttpxRequestException


async def get_all_play_info():
    """
    遍历set请求所有play的信息，获取的dataframe存在data文件夹，用于数据分析
    """
    time_start = perf_counter()
    try:
        df = pd.read_hdf(
            f'data/{str(datetime.date.today())}.h5', key='transaction_info')
    except:
        df = pd.DataFrame(columns=["set_id", "play_id", "player", "jersey_number",
                                   "circulation_count", "adjust_volume", "combine_transaction"])
    get_codex_result = None
    while get_codex_result is None:
        try:
            set_ids = await get_codex()
            for set_id in set_ids:
                get_codex_set_result = None
                while get_codex_set_result is None:
                    try:
                        id_pairs = await get_codex_set(set_id)
                        for id_pair in id_pairs:
                            if not df[(df['set_id'] == id_pair[0]) & (df['play_id'] == id_pair[1])].empty:
                                continue
                            result = None
                            while result is None:
                                try:
                                    result1 = await get_transactions(*id_pair)
                                    result2 = await get_transactions(*id_pair, by_highest=True)
                                    combine_history = sorted(
                                        list(set(result1[0]) | set(result2[0])), key=lambda a: a[1], reverse=True)
                                    combine_history = [(key, int(mean(map(lambda k:k[1], list(group)))))
                                                    for key, group in groupby(combine_history, lambda x: x[0])]
                                    df = df.append({
                                        "set_id": id_pair[0],
                                        "play_id": id_pair[1],
                                        "player": result1[3],
                                        "jersey_number": result1[4],
                                        "circulation_count": result1[2],
                                        "adjust_volume": result1[1],
                                        "combine_transaction": combine_history
                                    }, ignore_index=True)
                                    result = combine_history
                                    logger.info(
                                        f'处理 {id_pair[0]}+{id_pair[1]} 成功')
                                except Exception:
                                    logger.info(
                                        f'处理 {id_pair[0]}+{id_pair[1]} 失败，重试')
                        get_codex_set_result = id_pairs
                    except Exception:
                        logger.info(f'获取 {set_id} 失败，重试')

            df.to_hdf(f'data/{str(datetime.date.today())}.h5',key='transaction_info', mode='w')
            get_codex_result = set_ids
        except:
            logger.info(f'获取包信息失败，重试')
    time_end = perf_counter()
    logger.info(f'花费了{time_end-time_start}时间')

async def get_codex_info() -> Dict[str, Tuple[str, str]]:
    """
    获取所有包的信息

    Raises
    ------
    HttpxRequestException

    Return
    ------
    返回字典
    """
    url = base_market_url + "GetCodex="
    payload = {
        "operationName": "GetCodex",
        "variables": {
            "input": {
            }
        },
        "query": open('graphql/GetCodex.graphql').read()
    }
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, data=json.dumps(payload), headers=headers)
            response_json = r.json()
            set_ids = response_json['data']['getCodex']['codex']
            set_info_dict = dict()
            for i in set_ids:
                set_info_dict[i['set']['id']] = (i['set']['flowName'], i['set']
                                                 ['setVisualId'].split('_')[-1])
            return set_info_dict
    except Exception as e:
        logger.warning(f"httpx request error: {e}")
        raise HttpxRequestException