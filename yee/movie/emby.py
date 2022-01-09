from pandas import DataFrame

from yee.utils import number_utils, movie_utils
from yee.utils.http_utils import RequestUtils
import json
import re


class Emby:
    def __init__(self, host=None, port=None, api_key=None, is_https=False):
        self.req = RequestUtils()
        self.api_key = api_key
        self.host = host
        self.port = port
        self.is_https = is_https
        self.server = '%s://%s:%s' % ("https" if is_https else "http", host, port)

    def search(self, term, type='Movie,Series'):
        api = '/emby/Items'
        is_series = 'Series' in type
        term_arr = None
        if is_series:
            m_season = re.search('第.+季', term)
            if m_season:
                term_arr = [term, term.replace(m_season.group(), '').strip()]
        if term_arr is None:
            term_arr = [term]
        items = []
        # 多个关键词匹配结果最多的为准
        for t in term_arr:
            text = self.req.get(self.server + api,
                                params={'IncludeItemTypes': type, 'Recursive': 'true', 'SearchTerm': t,
                                        'api_key': self.api_key})
            json_data = json.loads(text)
            if len(json_data['Items']) > len(items):
                items = json_data['Items']
        return items

    def get_series_item_list(self, series_id):
        api = '/emby/Shows/%s/Episodes' % series_id
        text = self.req.get(self.server + api,
                            params={'api_key': self.api_key})
        json_data = json.loads(text)
        items = json_data['Items']
        for i in items:
            i['SeasonName'] = i['SeasonName'].replace('季 ', 'Season ')
        return items

    def get_miss_ep_index(self, season_number, total_ep_cnt, item_id):
        """
        获取缺少的分集信息索引
        这个地方的逻辑之所以这么复杂，就是因为有些剧名不规范的剧，在emby不一定能及时准确的识别到季和集信息，如果人肉手工及时识别到这些信息，就不会这么麻烦了
        :param season_number: 需要查找的季数
        :param total_ep_cnt: 这季剧的总集数
        :param item_id: 剧集在emby的id
        :return: 返回None为完全找不到本季分集信息；返回[]空数组为一集都不缺；返回[1,2]为具体缺少的分集数
        """
        series_item_list = self.get_series_item_list(item_id)
        series_name = series_item_list[0]['SeriesName']
        pd = DataFrame(series_item_list)
        pd_season_grouped = pd.groupby(by=['SeasonName'])
        group_season_name = 'Season %s' % season_number
        if group_season_name not in pd_season_grouped.groups.keys():
            first_season = next(iter(pd_season_grouped.groups.keys()))
            if re.match(r'Season \d+', first_season):
                # 是正常的季数信息，但与期望不匹配
                return None
            else:
                """
                逻辑走到这，可能是emby一些未识别或者未整理的剧集被搜索到了，先用自己的解析机制做一次验证
                根据名称匹配剧集信息的这个逻辑，可能会存在误差，但可能有效，会避免重复下载。这个有利有弊，后面可以改成配置，用户自己据测遇到这个case如何处理
                """
                ep_info = movie_utils.parse_episode_by_name(series_name, total_ep_cnt)
                if ep_info is None:
                    return None
                if season_number not in ep_info['season']['index']:
                    return None
                pd_season = pd_season_grouped.get_group(first_season)
        else:
            pd_season = pd_season_grouped.get_group(group_season_name)
        if pd_season is None:
            return None
        emby_season_cnt = len(pd_season)
        if pd_season is not None and emby_season_cnt == total_ep_cnt:
            return []
        else:
            miss_ep = list(
                set(number_utils.crate_number_list(1, total_ep_cnt)).difference(
                    set(pd_season['IndexNumber'].values.tolist())))
            miss_ep.sort()
            return miss_ep
