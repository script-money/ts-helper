from datetime import datetime
from typing import List, Tuple
import os

moment_info_type = Tuple[List[Tuple[int, int]], float, int, str, int]

def date_to_timestamp(time_str: str) -> float:
    """
    把时间格式改为时间戳

    Parameters
    ----------
    time_str: dapper的时间字符串
    
    Return
    ------
    时间戳，1位小数 
    """
    element = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
    return datetime.timestamp(element)


def calculate_adjust_volume(transactions_time:List) -> float:
    """
    根据交易时间列表计算日成交量

    Parameters
    ----------
    transactions_time: 成交时间列表
    
    Return
    ------
    日成交额，8位小数
    """
    count = len(transactions_time)
    if count != 1:
        return round(
        count/(date_to_timestamp(
        transactions_time[0])-date_to_timestamp(transactions_time[-1]))*60*60*24, 8)
    else:
        return 0


def compare_moments(old:List, new:List) -> List:
    """
    用于过滤连续两次的最新上架重叠部分，只对新的部分进行后续处理

    Parameters
    ----------
    old: 上一次MomentListing列表，从redis中读取
    new: 最新请求的MomentListing列表
    
    Return
    ------
    类型为 MomentListing 的列表

    """
    if old is None:
        return new
    old_ids = list(map(lambda m: m['id'], old))
    new_ids = list(map(lambda m: m['id'], new))
    last = old_ids[-1]
    if last in new_ids:
        return new[new_ids.index(last)+1:]
    return new


def calculate_reasonable_price(recent_transactions, adjust_volume, circulation_count, jersey_number) -> float:
    """
    根据最近的交易记录、成交量和流通量计算合理价格

    Parameters
    ----------
    recent_transactions: 最近成交记录，List[(flowNumber, price)]
    adjust_volume: 日成交量
    circulation_count: 流通量
    jersey_number: 球衣号码
    
    Return
    ------
    合理价格

    """
    # 需要一个函数，f(号数)->倍数。
    # 找多个moment数据集，通过价格倒序排序+最近成交来深度学习来确定函数。
    # 数据集用 coolcat 和 base2 的所有（需要过滤异常值）
    # 可以测试下 DTH 和 holo lock

    return 0.0


def get_last_file(path: str, contain: str=''):
    '''
    获取文件夹中最新文件路径

    Parameters
    ----------
    path: 子文件夹名
    contain: 包含字段
    
    Return
    ------
    最新文件路径 
    '''
    files = os.listdir(path)
    paths = [os.path.join(path, basename)
             for basename in files if contain in basename]
    return max(paths, key=os.path.getctime)

