from pandas import DataFrame
import re
import numpy as np
import math


class TorrentScoring:
    np.seterr(divide='ignore', invalid='ignore')
    # 原盘加分，此分值会同时加到类型分和字幕分
    __original_disc_keyword = ['港版原盘', '台版原盘']
    # 字幕加分，包含特定字幕关键字的标题会加分
    __subtitle_keyword = ['中字', '中文', '简繁', '双语', '中英']
    __type_score_match_name = {
        'UHD.*BluRay.*HEVC': 100,
        'UHD.*BluRay.*REMUX': 100,
        'UHD.*BluRay': 100,
        'WEB-?DL': 90,
        'Blu-?ray.*REMUX': 95,
        'Blu-?ray.*HEVC': 95,
        'Blu-?ray': 90,
        'TrueHD': 95,
        'DTS-?HD': 95,
        '2160p': 95,
        '1080p': 80,
    }
    __type_score = {
        'Movie(電影)/SD': 0,
        'Movie(電影)/HD': 80,
        'Movie(電影)/DVDiSo': 70,
        'Movie(電影)/Blu-Ray': 95,
        'Movie(電影)/Remux': 95,
        'TV Series(影劇/綜藝)/SD': 0,
        'TV Series(影劇/綜藝)/HD': 85,
        'TV Series(影劇/綜藝)/DVDiSo': 75,
        'TV Series(影劇/綜藝)/BD': 95,
        '紀錄教育': 100,
        'Anime(動畫)': 0,
        'MV(演唱)': 0,
        'Music(AAC/ALAC)': 0,
        'Music(無損)': 0,
        'Sports(運動)': 0,
        'Software(軟體)': 0,
        'PCGame(PC遊戲)': 0,
        'eBook(電子書)': 0,
        'AV(有碼)/HD Censored': 90,
        'AV(無碼)/HD Uncensored': 90,
        'AV(有碼)/SD Censored': 0,
        'AV(無碼)/SD Uncensored': 0,
        'AV(無碼)/DVDiSo Uncensored': 80,
        'AV(有碼)/DVDiSo Censored': 80,
        'AV(有碼)/Blu-Ray Censored': 100,
        'AV(無碼)/Blu-Ray Uncensored': 100,
        'AV(網站)/0Day': 0,
        'IV(寫真影集)/Video Collection': 0,
        'IV(寫真圖集)/Picture Collection': 0,
        'H-Game(遊戲)': 0,
        'H-Anime(動畫)': 0,
        'H-Comic(漫畫)': 0,
        'AV(Gay)/HD': 0,
        'Misc(其他)': 0,
    }

    def __get_type_score_by_name(self, str):
        for r in self.__type_score_match_name.keys():
            if re.search(r, str, re.IGNORECASE):
                return self.__type_score_match_name[r]
        return 0

    def __keywords_in_str(self, str, keywords, findall=True):
        match_cnt = 0
        for k in keywords:
            if k is None:
                continue
            if k in str:
                if findall:
                    match_cnt = match_cnt + 1
                else:
                    match_cnt = 1
                    break
        return match_cnt

    def reorder(self, torrent_list, **filter_param):
        """
        把种子的文件名、资源类型、文件大小、做种上传量、下载量等信息归一化，并按特定权重打分，然后按分值排序
        :param torrent_list:
        :param name_keywords:
        :param series:剧集配置，提供丰富的剧集配置，可以针对剧集资源做更有效的打分
        :return:
        """
        if torrent_list is None or len(torrent_list) == 0:
            return None
        pd = DataFrame(torrent_list)
        pd['upload_score'] = list(self.__normalization(pd['upload_count'].tolist()))
        pd['download_score'] = list(self.__normalization(pd['download_count'].tolist()))
        pd['file_size_score'] = list(self.__normalization(pd['file_size'].tolist()))
        type_score = []
        subtitle_score = []
        name_score = []
        for index, row in pd.iterrows():
            subject = row['subject']
            original_disk_score = self.__keywords_in_str(subject, self.__original_disc_keyword, findall=False) * 100
            subtitle_score.append(self.__keywords_in_str(subject, self.__subtitle_keyword) + original_disk_score)
            ts = max(self.__type_score[row['type_str']],
                     self.__get_type_score_by_name(row['name'])) + original_disk_score
            type_score.append(ts)
            ns = max(self.__keywords_in_str(subject, filter_param['name_keywords']),
                     self.__keywords_in_str(row['name'], filter_param['name_keywords']))
            if filter_param['series'] is not None:
                ep = filter_param['series']['episode']
                row_ep = row['episode']
                # 如果是剧集，能够匹配到全集的资源，分数加100，最优选择;大于等于是因为豆瓣的剧集信息有可能不准，会少
                if len(row_ep['ep']['index']) >= ep:
                    # 如果名称中没提供集数信息，而是自动补全的，分数g给一半，在有全集和只有名称没全集的情况下，有全集标识的，应该优先
                    if row_ep['ep']['auto_ep']:
                        series_complete_score = 50
                    else:
                        series_complete_score = 100
                else:
                    series_complete_score = 0
                ns = ns + series_complete_score

            name_score.append(ns)

        pd['subtitle_score'] = list(self.__normalization(subtitle_score))
        pd['name_score'] = list(self.__normalization(name_score))
        pd['type_score'] = list(self.__normalization(type_score))
        pd['score'] = pd.apply(
            lambda x: self.__cal_score(x), axis=1)
        pd = pd.sort_values(by=['score'], ascending=False)
        return pd

    def __cal_score(self, pd_row):
        weights = {
            'name_score': 0.40,
            'type_score': 0.225,
            'file_size_score': 0.15,
            'upload_score': 0.125,
            'download_score': 0.05,
            'subtitle_score': 0.05
        }
        score = 0
        for key in weights:
            if math.isnan(pd_row[key]):
                continue
            score = score + pd_row[key] * weights[key]
        return score

    def __normalization(self, data):
        _range = np.max(data) - np.min(data)
        return (data - np.min(data)) / _range
