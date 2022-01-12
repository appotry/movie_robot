import datetime
import html
import os
import re
import time
import urllib.parse
import urllib.parse as urlparse
from http.cookiejar import Cookie

from lxml import etree

from yee.movie.douban import DoubanMovie
from yee.pt.torrent_scoring import TorrentScoring
from yee.utils import movie_utils
from yee.utils.http_utils import RequestUtils
from requests.cookies import RequestsCookieJar


class MTeam:
    def __init__(self, username=None, password=None, cookie=None):
        self.req = RequestUtils(request_interval_mode=True)
        if username is not None and username.strip() != '':
            self.login(username, password)
        elif cookie is not None and cookie.strip() != '':
            self.login_by_cookie(cookie)
        else:
            raise RuntimeError('必须提供登陆信息才可以试用MTeam！')
        self.douban = DoubanMovie()
        self.torrent = TorrentScoring()

    def login_by_cookie(self, cookie):
        cookie_arr = cookie.split(';')
        cookie_jar = RequestsCookieJar()
        # 默认设30天过期
        expire = round(time.time()) + 60 * 60 * 24 * 30
        for c in cookie_arr:
            pair = c.strip().split('=')
            cookie = Cookie(0, pair[0], pair[1], None, False, 'kp.m-team.cc', False, False, '/', True, True, expire,
                            False, None,
                            None, [], False)
            cookie_jar.set_cookie(cookie)
        res = self.req.get_res(
            'https://kp.m-team.cc/',
            headers={
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36'
            }, cookies=cookie_jar
        )
        match_login_user = re.search(r'class=\'EliteUser_Name\'><b>(.+)</b></a></span>', res.text)
        if res is None or not match_login_user:
            raise RuntimeError('登陆失败')
        self.cookies = cookie_jar
        print('MTeam登陆成功，欢迎回来：%s' % match_login_user.group(1))

    def login(self, username, password):
        res = self.req.post_res(
            'https://kp.m-team.cc/takelogin.php',
            params={'username': username, 'password': password},
            headers={
                'referer': 'https://kp.m-teaself.cc/login.php',
                'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36'
            },
            allow_redirects=False
        )
        if res == None:
            raise RuntimeError('访问MTeam异常')
        if res.status_code != 302:
            raise RuntimeError('登陆失败')
        self.cookies = res.cookies
        print('MTeam登陆成功，欢迎回来：%s' % username)

    def search_by_douban_movie(self, movie, **filter_params):
        if movie is None:
            return None
        search_name = movie['name']
        local_name = movie['local_name']
        # 用电影本地名、别名，给搜索结果匹配项加分
        name_keywords = [local_name] + movie['alias']
        name_keywords = list(filter(None, name_keywords))
        type_list = [movie['type']]
        cate_list = movie['cate']
        # todo 真人秀、纪录片、脱口秀分类处理
        if cate_list is not None and '纪录片' in cate_list:
            type_list.append('Documentary')
        if cate_list is not None and '脱口秀' in cate_list:
            type_list.append('Documentary')
        if cate_list is not None and '真人秀' in cate_list:
            type_list.append('Documentary')
        series = None
        if movie['type'] == 'Series':
            series = {'episode': movie['episode']}
        search_filter = {
            'year': movie['year'], 'types': type_list, 'name_keywords': name_keywords, 'series': series
        }
        if search_filter is not None:
            search_filter.update(filter_params)
        r = self.search(search_name, **search_filter)
        if r is None:
            return None
        return r

    def search_by_douban_id(self, id, **filter_param):
        movie = self.douban.get_movie_by_id(id)
        return self.search_by_douban_movie(movie, **filter_param)

    def search(self, keyword, **filter_param):
        next_page = 0
        search_result = []
        all_publish_time = []
        while next_page is not None:
            res = self.req.get_res(
                "https://kp.m-team.cc/torrents.php?incldead=1&spstate=0&inclbookmarked=0&search=%s&search_area=0&search_mode=0&page=%s" % (
                    urllib.parse.quote_plus(
                        keyword), next_page),
                cookies=self.cookies)
            self.cookies.update(res.cookies)
            text = res.text
            match_page = re.findall(r'page=(\d+)"><b\s+title="Alt\+Pagedown">下一頁', text)
            if len(match_page) > 0:
                next_page = match_page[0]
            else:
                next_page = None
            ehtml = etree.HTML(res.text)
            # 下载链接
            download_list = [str(s) for s in
                             ehtml.xpath(
                                 '//table[@class="torrentname"]/tr/td/a[starts-with(@href,"download.php")]/@href')]
            if len(download_list) == 0:
                return None
            # 种子发布时间
            publish_time_list = re.findall(r'<span title="(\d{4}-\d{2}-\d{1,2} \d{2}:\d{2}:\d{2})">', text)
            all_publish_time = all_publish_time + publish_time_list
            # 视频类型
            type_list = [str(s).strip() for s in
                         ehtml.xpath('//table[@class="torrents"]/tr/td[@class="rowfollow nowrap"]/a/img/@title')]
            torrent_name_list = []
            subject_list = []
            # 正则匹配种子名称和副标题
            match_name = re.findall(r'<b>.+</b>.*</td><td width="80" class="embedded"', res.text)
            for match_upload_cnt in match_name:
                torrent_name_list.append(html.unescape(re.match(r'<b>([^<]+)</b>', match_upload_cnt).group(1)))
                m_subject = re.match(r'.+<br />(.+)</td>', match_upload_cnt)
                # 副标题可能为空
                if m_subject is not None:
                    subject_list.append(html.unescape(m_subject.group(1)))
                else:
                    subject_list.append('')
            # 种子大小
            file_size_td = ehtml.xpath('//tr/td[@class="rowfollow" and number(text())]/text()')
            file_size_list = []
            i = 0
            # 一行是尺寸 一行是单位。把尺寸全部转为MB
            while i < len(file_size_td):
                unit = str(file_size_td[i + 1]).strip()
                size = float(str(file_size_td[i]))
                if unit == 'GB':
                    file_size_list.append(round(size * 1024, 2))
                elif unit == 'MB':
                    file_size_list.append(round(size, 2))
                elif unit == 'KB':
                    file_size_list.append(round(size / 1024, 2))
                elif unit == 'TB':
                    file_size_list.append(round(size * 1024 * 1024, 2))
                i = i + 2
            # 下载数量
            match_download_cnt_list = re.findall(
                r'<td\s+class="rowfollow">(?:<a\s+href="viewsnatches.php?id=\d+"><b>)?(.+)(?:</b></a>)?</td>\s*<td\s+class="rowfollow(?: peer-active)?"\s+style="font-weight: bold">',
                res.text)
            # 上传数量
            match_upload_cnt_list = re.findall(
                r'<td\s+class=\"rowfollow\"(?:\s+align=\"center\")?>(?:<span\s*class=\"red\">\d+</span>)|(?:<b><a\s*href=\".+seeders\">(?:<font\s+color="(#.+)">)?(.+)(?:</font>)?</a></b>)',
                res.text)
            for i in range(len(download_list)):
                match_upload_cnt = match_upload_cnt_list[i]
                upload_count = match_upload_cnt[1]
                if upload_count == '':
                    # 为0的红种子
                    continue
                elif match_upload_cnt[0] != '':
                    # 其他颜色上传的种子，值为色号
                    continue
                # 可能匹配到<a href="viewsnatches.php?id=523258"><b>1,568</b>，再做一次精确提取
                match_upload_cnt = re.match('.+<b>(.+)</b>.+', match_download_cnt_list[i])
                if match_upload_cnt is None:
                    download_count = match_download_cnt_list[i]
                else:
                    download_count = match_upload_cnt.group(1)
                subject = subject_list[i]
                torrent_name = torrent_name_list[i]
                torrent_year = movie_utils.parse_year_by_str(subject)
                if torrent_year is None:
                    torrent_year = movie_utils.parse_year_by_str(torrent_name)
                if torrent_year is not None:
                    if torrent_year != filter_param['year']:
                        # 种子年份信息与实际想要的年份不符
                        continue
                type_str = type_list[i]
                # 把meteam上的资源类型（某一类会分出多个清晰度类型），转成可过滤的标准资源类型
                if type_str.startswith('Movie'):
                    type = 'Movie'
                elif type_str.startswith('TV Series'):
                    type = 'Series'
                elif type_str.startswith('Music'):
                    type = 'Music'
                elif type_str.startswith('紀錄教育'):
                    type = 'Documentary'
                elif type_str.startswith('AV'):
                    type = 'AV'
                else:
                    type = 'Other'
                if filter_param['types'] is not None and type != 'Other' and type not in filter_param['types']:
                    continue
                episode = None
                if type == 'Series' or type == 'Documentary' or type == 'Other':
                    episode = movie_utils.parse_episode_by_name(subject,
                                                                filter_param['series']['episode'] if filter_param[
                                                                                                         'series'] is not None else None)
                upload_count = int(upload_count.replace(',', ''))
                publish_time = datetime.datetime.strptime(publish_time_list[i], '%Y-%m-%d %H:%M:%S')
                search_result.append(
                    {
                        'subject': subject,
                        'name': torrent_name,
                        'year': torrent_year,
                        'episode': episode,
                        'url': 'https://kp.m-team.cc/' + download_list[i],
                        'type': type,
                        'type_str': type_str,
                        'file_size': file_size_list[i],
                        'upload_count': upload_count,
                        'download_count': int(download_count.replace(',', '')),
                        'publish_time': publish_time
                    }
                )
        all_publish_time.sort()
        if 'first_torrent_passed_hours' in filter_param and filter_param['first_torrent_passed_hours'] is not None:
            start_passed_hours = round((datetime.datetime.now() - datetime.datetime.strptime(all_publish_time[0],
                                                                                             '%Y-%m-%d %H:%M:%S')).seconds / 60 / 60,
                                       2)
            if start_passed_hours < filter_param['first_torrent_passed_hours']:
                print(
                    '%s首个种子（%s）发布时间仅%s小时，未达到配置的%s小时要求，跳过本次搜索' % (keyword,
                                                                 subject, start_passed_hours,
                                                                 filter_param['first_torrent_passed_hours']))
                return None
        pd = self.torrent.reorder(search_result, **filter_param)
        if pd is None:
            return None
        return pd.to_dict('records')

    def download_torrent(self, url, filedir):
        r = self.req.get_res(url, headers={
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'referer': 'https://kp.m-team.cc/torrents.php',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36'
        }, cookies=self.cookies)
        parsed = urlparse.urlparse(r.url)
        querys = urlparse.parse_qs(parsed.query)
        save_filepath = filedir + os.sep + querys['name'][0] + '.torrent'
        querys['save_filepath'] = save_filepath
        # 本地如果已经存在则不下载了
        if os.path.exists(save_filepath):
            return querys
        with open(save_filepath, 'wb') as f:
            f.write(r.content)
        return querys
