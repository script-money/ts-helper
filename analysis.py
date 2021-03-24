from request import get_codex
from statistics import mean
from itertools import groupby
import pandas as pd
import numpy as np
from utils import get_last_file

data_path = './data'
csv_path = './csv'

async def generate_csv():
    def load_h5(path):
        df = pd.read_hdf(path)
        df = df[df['player'] != ""]  # 去掉player为na的
        df = df[df['adjust_volume'] > 0.5] # 去掉日成交量不足0.5的

        def get_basic_value(df):
            recent_trans = df['recent_transaction']
            volume = df['adjust_volume']
            low_list_price = df['low_list_price']
            recent_prices = list(map(lambda a: a[1], recent_trans))  # 第一个是最近的
            # 如果是日成交量小于1.5的，按挂单价计算;
            if volume < 1.5 and low_list_price != 0:
                return low_list_price
            # 没挂单的直接按最新成交算
            elif low_list_price == 0:
                return recent_trans[0][1]
            # 否则按最近3笔的中间一笔计算
            else:
                return np.median(recent_prices[:3])

        def combine_history(df):
            combine_history = sorted(
                list(set(df['highest_transaction']) | set(df['recent_transaction'])), key=lambda a: a[1], reverse=True)
            combine_history = [(key, int(mean(map(lambda k:k[1], list(group)))))
                            for key, group in groupby(combine_history, lambda x: x[0])]
            return combine_history

        def calculate_list_count_ratio(df):
            count = len(df['list_detail'])
            return count/df['circulation_count']

        df['combine_transaction'] = df.apply(combine_history, axis=1)
        df['baseline_price'] = df.apply(get_basic_value, axis=1)
        df['baseline_cap'] = df['baseline_price'] * \
            df['circulation_count'].astype(float)
        df['list_count_ratio'] = df.apply(calculate_list_count_ratio, axis=1)

        # 计算占同球员其他play占比，获得百分比
        mean_player_group = df.groupby(['player']).mean()
    
        def get_player_baseline_cap_ratio(df1):
            cap = df1['baseline_cap']   
            target_mean = mean_player_group.loc[df1['player']]['baseline_cap']
            return cap/target_mean
        df['player_baseline_cap_ratio'] = df.apply(
            get_player_baseline_cap_ratio, axis=1)

        # 计算在同set的占比，获得百分比
        mean_set_id_group = df.groupby(['set_id']).mean()

        def get_set_id_baseline_cap_ratio(df2):
            cap = df2['baseline_cap']
            target_mean = mean_set_id_group.loc[df2['set_id']]['baseline_cap']
            return cap/target_mean
        df['set_id_baseline_cap_ratio'] = df.apply(
            get_set_id_baseline_cap_ratio, axis=1)

        return df

    df = load_h5(get_last_file(data_path, 'h5'))

    def is_jersey_traded(df):
        transactions = df['combine_transaction']
        jersey = df["jersey_number"]
        numbers = list(map(lambda a: a[0], transactions))
        return jersey in numbers

    df['contain_jersey'] = df.apply(is_jersey_traded, axis=1)

    def get_jersey_ratio(df):
        transactions = df['combine_transaction']
        baseline = df['baseline_cap']
        jersey = df["jersey_number"]
        for transaction in transactions:
            if transaction[0] == jersey:
                return transaction[1]/baseline

    df['jersey_ratio'] = df.apply(get_jersey_ratio, axis=1)

    def is_first_traded(df):
        transactions = df['combine_transaction']
        numbers = list(map(lambda a: a[0], transactions))
        return 1 in numbers

    df['contain_first'] = df.apply(is_first_traded, axis=1)

    def get_first_ratio(df):
        transactions = df['combine_transaction']
        baseline = df['baseline_cap']
        if transactions[0][0] == 1:
            return transactions[0][1]/baseline

    df['first_ratio'] = df.apply(get_first_ratio, axis=1)

    def is_last_traded(df):
        transactions = df['combine_transaction']
        last = df["circulation_count"]
        numbers = list(map(lambda a: a[0], transactions))
        return last in numbers

    df['contain_last'] = df.apply(is_last_traded, axis=1)

    def get_last_ratio(df):
        transactions = df['combine_transaction']
        baseline = df['baseline_cap']
        last = df["circulation_count"]
        count = last
        for transaction in transactions:
            if transaction[0] == last:
                return transaction[1]/baseline

    df['last_ratio'] = df.apply(get_last_ratio, axis=1)

    async def export_readable_csv(df, file_name):
        df = df.reset_index(drop=True)
        df['set_name'] = df['set_id'].copy()
        set_info = await get_codex()
        set_id_name_dict = dict((x, y) for x, y in set_info)
        df = df.replace({"set_name": set_id_name_dict})
        df['moment_list_url'] = "https://www.nbatopshot.com/listings/p2p/" + \
            df['set_id']+'+'+df['play_id']
        df['recent_transaction'] = df['recent_transaction'].apply(lambda l: l[:3])
        df['highest_transaction'] = df['highest_transaction'].apply(
            lambda l: l[:3])
        df['baseline_price'] = df['baseline_price'].apply(lambda i: int(i))
        df['low_list_price'] = df['low_list_price'].apply(lambda i: int(i))
        df['baseline_cap'] = df['baseline_cap'].apply(lambda i: f'{int(i):,}')
        df['adjust_volume'] = df['adjust_volume'].apply(lambda v: f'{v:.2f}')
        df['list_count_ratio'] = df['list_count_ratio'].apply(
            lambda v: "{:.2%}".format(v))
        df['player_baseline_cap_ratio'] = df['player_baseline_cap_ratio'].apply(
            lambda v: "{:.2%}".format(v))
        df['set_id_baseline_cap_ratio'] = df['set_id_baseline_cap_ratio'].apply(
            lambda v: "{:.2%}".format(v))
        # 丢弃的column
        df = df.drop(['set_id', 'play_id', 'jersey_number', 'contain_jersey', 'low_list_price', 'jersey_ratio', 'contain_first',
                    'combine_transaction', 'first_ratio', 'contain_last', 'last_ratio', 'recent_transaction', 'highest_transaction'], axis=1)
        cols = ['player', 'set_name', 'circulation_count', 'baseline_price', 'baseline_cap', 'adjust_volume',
                'list_count_ratio', 'player_baseline_cap_ratio', 'set_id_baseline_cap_ratio', 'moment_list_url']
        col_name_mapper = {
            'player': '球员',
            'set_name': '包名',
            'circulation_count': '总数',
            'baseline_price': '单价',
            'baseline_cap': '市值',
            'adjust_volume': '日成交量',
            'moment_list_url': '页面地址',
            'list_count_ratio': '挂单流通比',
            'player_baseline_cap_ratio': '同球员市值占比',
            'set_id_baseline_cap_ratio': '同包市值占比'
        }

        df = df[cols]
        df = df.rename(columns=col_name_mapper)
        df.to_csv(file_name)
        return df

    await export_readable_csv(df, get_last_file(data_path, 'h5').replace('h5', 'csv').replace(data_path, csv_path))
