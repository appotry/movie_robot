import argparse
import datetime
import os
import sys
from yee.movie.downloader import Downloader
import yaml

user_setting_name = 'user_config.yml'


def init_default_user_setting(filepath):
    default_config = {
        'downloader': {'delete_torrent': False, 'save_mode': [
            {
                'type': '电影',
                'cate': '纪录片',
                'my_cate': '纪录片'
            }, {
                'type': '剧集',
                'cate': '纪录片',
                'my_cate': '纪录片'
            }, {
                'cate': '真人秀',
                'my_cate': '综艺'
            }, {
                'cate': '脱口秀',
                'my_cate': '综艺'
            }, {
                'type': '电影',
                'my_cate': '电影',
                'path': '/video/电影'
            }, {
                'type': '剧集',
                'my_cate': '电视节目'
            }
        ]},
        'douban': {'user_domain': 'user1;user2', 'within_days': 365, 'turn_page': True,
                   'types': 'wish'},
        'emby': {'host': 'your_emby_host', 'port': 8080, 'api_key': 'your_api_key',
                 'https': False},
        'qbittorrent': {'url': 'http://your_host:8080/', 'need_login': False, 'username': 'admin',
                        'password': 'admin'},
        'mteam': {'username': 'your_username', 'password': 'your_password'}
    }
    with open(filepath, 'w', encoding='utf-8') as file:
        yaml.dump(default_config, file, allow_unicode=True)


def load_user_config():
    user_setting_filepath = args.workdir + os.sep + user_setting_name
    if not os.path.exists(user_setting_filepath):
        init_default_user_setting(user_setting_filepath)
        print('%s 配置文件不存在，已经为你创建了一个默认的配置文件，请更改关键配置后重启，或更改后等待下一次调度运行。' % user_setting_filepath)
        sys.exit()
    with open(user_setting_filepath, 'r', encoding='utf-8') as file:
        user_config = yaml.safe_load(file)
    return user_config


def parser_args():
    parser = argparse.ArgumentParser(description='豆瓣电影自动下载器')
    parser.add_argument('-w', '--workdir', required=True, type=str, help='程序运行的工作目录（配置文件、种子临时下载目录）')
    args = parser.parse_args()
    return args


def build_downloader(user_config, workdir):
    params = {
        'workdir': workdir,
        'downloader': {
            'delete_torrent': user_config['downloader']['delete_torrent'],
            'save_mode': user_config['downloader']['save_mode']
        },
        'douban': {
            'user_domain': str(user_config['douban']['user_domain']).split(';'),
            'within_days': user_config['douban']['within_days'],
            'turn_page': user_config['douban']['turn_page'],
            'types': user_config['douban']['types'].split(';')
        },
        'emby': {
            'host': user_config['emby']['host'],
            'port': user_config['emby']['port'],
            'api_key': user_config['emby']['api_key'],
            'https': user_config['emby']['https']
        },
        'qbittorrent': {
            'url': user_config['qbittorrent']['url'],
            'need_login': user_config['qbittorrent']['need_login'],
            'username': user_config['qbittorrent']['username'],
            'password': user_config['qbittorrent']['password']
        },
        'mteam': {
            'username': user_config['mteam']['username'],
            'password': user_config['mteam']['password']
        }
    }
    return Downloader(**params)


if __name__ == '__main__':
    args = parser_args()
    workdir = args.workdir
    if not os.path.exists(workdir):
        print('请提供正确的配置，工作目录不存在：%s' % workdir)
        sys.exit()
    config = load_user_config()
    downloader = build_downloader(config, workdir)
    print('开始寻找电影并自动找种下载，现在时间是 %s' % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    downloader.start()
