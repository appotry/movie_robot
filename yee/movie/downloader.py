import os
from qbittorrent import Client

import yee.pt.torrent as tt
from yee.movie.douban import DoubanMovie
from yee.movie.emby import Emby
from yee.pt.mteam import MTeam


class Downloader:
    def __init__(self, **kwargs):
        self.workdir = kwargs['workdir']
        self.delete_torrent = kwargs['downloader']['delete_torrent']
        self.save_mode = kwargs['downloader']['save_mode']
        self.first_torrent_passed_hours = kwargs['downloader']['first_torrent_passed_hours']
        self.douban_config = kwargs['douban']
        self.douban = DoubanMovie()
        self.mteam = MTeam(username=kwargs['mteam']['username'], password=kwargs['mteam']['password'],
                           cookie=kwargs['mteam']['cookie'])
        self.emby = Emby(
            host=kwargs['emby']['host'],
            port=kwargs['emby']['port'],
            api_key=kwargs['emby']['api_key'],
            is_https=kwargs['emby']['https']
        )
        self.qb = Client(kwargs['qbittorrent']['url'])
        if kwargs['qbittorrent']['need_login']:
            self.qb.login(kwargs['qbittorrent']['username'], kwargs['qbittorrent']['password'])

    def start(self):
        users = self.douban_config['user_domain']
        for u in users:
            self.search_and_download(
                u,
                types=self.douban_config['types'],
                within_days=self.douban_config['within_days'],
                turn_page=self.douban_config['turn_page'],
                first_torrent_passed_hours=self.first_torrent_passed_hours
            )
        print('所有用户的影视下载已经完成。')

    def get_best_torrent(self, douban_movie, **filter_params):
        torrent_list = self.mteam.search_by_douban_movie(douban_movie, **filter_params)
        if torrent_list is None:
            return None
        return torrent_list[0]

    def __check_param_is_empty(self, params, key):
        if key not in params:
            return True
        val = params[key]
        if val is None:
            return True
        if type(val) == str and val.strip() == '':
            return True
        if type(val) == list and len(val) == 0:
            return True
        return False

    def search_and_download(self, douban_user, **filter_params):
        if self.__check_param_is_empty(filter_params, 'types'):
            filter_params['types'] = ['wish']
        if self.__check_param_is_empty(filter_params, 'within_days'):
            filter_params['within_days'] = 365
        if self.__check_param_is_empty(filter_params, 'turn_page'):
            filter_params['turn_page'] = True
        movie_list = self.douban.get_user_movie_list(douban_user, types=filter_params['types'],
                                                     within_days=filter_params['within_days'],
                                                     turn_page=filter_params['turn_page'])
        if movie_list is None:
            print('%s没有任何影视资源需要下载' % douban_user)
            return None
        print('已经获得%s的全部影视，共有%s个需要智能检索' % (douban_user, len(movie_list)))
        for douban_list_item in movie_list:
            movie_detail = self.douban.get_movie_by_id(douban_list_item['id'])
            if movie_detail is None:
                print('%s(id:%s)信息获取异常' % (douban_list_item['name'], douban_list_item['id']))
                continue
            type = movie_detail['type']
            is_series = 'Series' == type
            search_name = douban_list_item['name']
            item_list = self.emby.search(search_name, type=type)
            miss_ep_index = None
            if len(item_list) > 0:
                if is_series:
                    # 把本地影视库匹配到的每个结果，都做一次剧集检测
                    for item in item_list:
                        miss_ep_index = self.emby.get_miss_ep_index(movie_detail['season_number'],
                                                                    movie_detail['episode'],
                                                                    item['Id'])
                        if miss_ep_index is not None:
                            break
                    if miss_ep_index is not None and len(miss_ep_index) == 0:
                        print('%s在影视库为剧集，总共%s集全部下载完毕，跳过处理' % (search_name, movie_detail['episode']))
                        continue
                else:
                    print('%s在影视库存在，跳过处理' % search_name)
                    continue
            if miss_ep_index is None:
                # 完全没有的剧集或电影
                print('%s需要下载，开始寻找种子...' % search_name)
                # 取分最高的一个
                best_choice = self.get_best_torrent(movie_detail, first_torrent_passed_hours=filter_params['first_torrent_passed_hours'])
                if best_choice is None:
                    print('找不到与%s有关的种子！' % search_name)
                    continue
                print('%s的最佳种子为 %s' % (search_name, best_choice['name']))
                self.download(best_choice, movie_detail)
            else:
                print('开始查找%s的第%s集' % (search_name, miss_ep_index))
                torrent_list = self.mteam.search_by_douban_movie(movie_detail)
                if torrent_list is None:
                    print('找不到%s的任何资源' % search_name)
                    continue
                torrent_list = tt.find_torrent_by_episodes(torrent_list, search_index=miss_ep_index)
                if len(torrent_list) == 0:
                    print('找不到%s的%s剧集' % (search_name, miss_ep_index))
                    continue
                for ep_idx in miss_ep_index:
                    # 检查缺少的剧集，是否在当前种子列表，如果存在就自动下载
                    for torrent in torrent_list:
                        if tt.check_ep_in_torrent(torrent, search_ep_index=[ep_idx]):
                            print('%s的第%s集最佳种子为 %s' % (search_name, ep_idx, torrent['name']))
                            self.download(torrent, movie_detail)
                            break

    @staticmethod
    def __mode_key_is_not_empty(mode, key):
        if key not in mode:
            return False
        str = mode[key]
        if str is not None and str.strip() != '':
            return True
        else:
            return False

    @staticmethod
    def __mode_result(mode):
        return {
            'my_cate': mode['my_cate'] if 'my_cate' in mode else None,
            'path': mode['path'] if 'path' in mode else None
        }

    def get_save_mode(self, douban_type, douban_cate_list):
        for mode in self.save_mode:
            if self.__mode_key_is_not_empty(mode, 'type') and self.__mode_key_is_not_empty(mode, 'cate'):
                # 都要匹配
                if mode['type'] == douban_type and mode['cate'] in douban_cate_list:
                    return self.__mode_result(mode)
            elif self.__mode_key_is_not_empty(mode, 'type') and not self.__mode_key_is_not_empty(mode, 'cate'):
                # 只需要匹配type
                if mode['type'] == douban_type:
                    return self.__mode_result(mode)
            else:
                # 只需要匹配cate
                if mode['cate'] in douban_cate_list:
                    return self.__mode_result(mode)
        return {
            'my_cate': None,
            'path': None
        }

    douban_type_to_cn = {'Movie': '电影', 'Series': '剧集'}

    def download(self, torrent, douban_movie):
        torrent_dir = self.workdir + os.sep + 'torrent'
        if not os.path.exists(torrent_dir):
            os.mkdir(torrent_dir)
        save_mode = self.get_save_mode(self.douban_type_to_cn[douban_movie['type']], douban_movie['cate'])
        file_data = self.mteam.download_torrent(torrent['url'], torrent_dir)
        hash = tt.info_hash(file_data['save_filepath'])
        torrents_in_qbit = list(filter(lambda x: x['hash'] == hash, self.qb.torrents()))
        if len(torrents_in_qbit) > 0:
            print('%s在qbit中已经存在，跳过下载' % file_data['name'][0])
        else:
            # return 'Ok.'/'Fails.'
            dr = self.qb.download_from_file(open(file_data['save_filepath'], 'rb'), savepath=save_mode['path'],
                                            category=save_mode['my_cate'])
            if dr == 'Ok.':
                print('%s已经开始下载 保存分类：%s 路径：%s' % (torrent['subject'], save_mode['my_cate'], save_mode['path']))
            else:
                print('%s提交qbit下载失败' % file_data['name'][0])
        if self.delete_torrent:
            os.remove(file_data['save_filepath'])
