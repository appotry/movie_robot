class TorrentSearch:
    @staticmethod
    def check_ep_in_torrent(torrent, search_season_number=[], search_ep_index=[]):
        """
        验证一个种子是否包含选定的剧集季和分集
        :param torrent:
        :param search_season_number:
        :param search_ep_index:
        :return:
        """
        if 'episode' not in torrent:
            return False
        if 'ep' not in torrent['episode']:
            return False
        if search_season_number is not None and len(search_season_number) > 0:
            if 'season' not in torrent['episode']:
                return False
            season_in = list(set(torrent['episode']['season']['index']).intersection(set(search_season_number)))
            if len(season_in) == 0:
                return False
        torrent_ep_index = torrent['episode']['ep']['index']
        ep_in = list(set(torrent_ep_index).intersection(set(search_ep_index)))
        return len(ep_in) > 0

    @staticmethod
    def find_torrent_by_episodes(torrent_list, search_season_number=[], search_index=[]):
        """
        查找种子中存在指定剧集的资源，返回结果会按集数排序
        :param torrent_list:种子信息（需要包含剧集信息）
        :param search_season_number:需要检索的剧集索引
        :param search_index:需要检索的集数
        :return:
        """
        if search_index is None or len(search_index) == 0:
            return []
        # 把完全不包含想要剧集的种子过滤掉
        torrent_list = list(
            filter(lambda x: TorrentSearch.check_ep_in_torrent(x, search_season_number, search_index), torrent_list))
        # 集数正序，尽量下载单集资源
        torrent_list.sort(key=lambda x: len(x['episode']['ep']['index']))
        return torrent_list
