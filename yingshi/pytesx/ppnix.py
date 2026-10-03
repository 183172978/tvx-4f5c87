# -*- coding: utf-8 -*-
# PPnix https://www.ppnix.com/cn/
# 结构参考爱奇艺源；播放直链 m3u8 parse=0
import re
import sys
from urllib.parse import quote

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def init(self, extend=''):
            pass


class Spider(Spider):

    def init(self, extend=""):
        pass

    def getName(self):
        return 'PPnix'

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return any(x in u for x in ('.mp4', '.m3u8', '.flv', '.mkv'))

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    rhost = 'https://www.ppnix.com'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        'Referer': 'https://www.ppnix.com/cn/',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    # type_id: path segment under /cn/
    cateManual = {
        '电影': 'movie',
        '电视剧': 'tv',
        '电影·剧情': 'movie/剧情',
        '电影·喜剧': 'movie/喜剧',
        '电影·动作': 'movie/动作',
        '电影·爱情': 'movie/爱情',
        '电影·科幻': 'movie/科幻',
        '电影·恐怖': 'movie/恐怖',
        '电影·动画': 'movie/动画',
        '电影·悬疑': 'movie/悬疑',
    }

    def fetch(self, url, headers=None):
        import requests
        r = requests.get(url, headers=headers or self.headers, timeout=20)
        return r

    def homeContent(self, filter):
        classes = [{'type_name': k, 'type_id': v} for k, v in self.cateManual.items()]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        html = self.fetch(self.rhost + '/cn/').text
        return {'list': self._parse_list(html)[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = str(tid).strip('/')
        # 分页规则: /cn/movie/---2-.html  或  /cn/movie/剧情---2-.html
        if '/' in tid:
            # genre: movie/剧情
            base, genre = tid.split('/', 1)
            if pg <= 1:
                path = f'/cn/{base}/{genre}----.html'
            else:
                path = f'/cn/{base}/{genre}---{pg}-.html'
        else:
            if pg <= 1:
                path = f'/cn/{tid}/'
            else:
                path = f'/cn/{tid}/---{pg}-.html'
        html = self.fetch(self.rhost + path).text
        videos = self._parse_list(html)
        pagecount = pg + 1 if len(videos) >= 20 else pg
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': 24,
            'total': 999999,
        }

    def _parse_list(self, html):
        videos = []
        seen = set()
        if not html:
            return videos
        for m in re.finditer(
            r'<a href="(/cn/(?:movie|tv)/(\d+)\.html)"[^>]*class="thumbnail"[^>]*>\s*'
            r'<img[^>]+src="([^"]*)"[^>]*alt="([^"]*)"',
            html,
            re.I,
        ):
            path, pid, pic, alt = m.groups()
            if pid in seen:
                continue
            seen.add(pid)
            videos.append({
                'vod_id': path,
                'vod_name': (alt or pid).strip(),
                'vod_pic': pic,
                'vod_remarks': '',
            })
        return videos

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, list) else ids
        path = str(raw)
        if not path.startswith('/'):
            path = '/cn/movie/' + path
        if not path.endswith('.html'):
            path = path.rstrip('/') + '.html'
        url = self.rhost + path
        html = self.fetch(url).text

        title = ''
        tm = re.search(r'<title>([^<]+)</title>', html, re.I)
        if tm:
            title = tm.group(1).split(' - ')[0].strip()
            title = re.sub(r'\s*\(\d{4}\)\s*$', '', title).strip()

        pic = ''
        pm = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
        if not pm:
            pm = re.search(r'class="thumbnail"[^>]*>\s*<img[^>]+src="([^"]+)"', html, re.I)
        if pm:
            pic = pm.group(1)

        # classid / infoid / m3u8 列表
        infoid = ''
        im = re.search(r'infoid\s*=\s*[\'"]?(\d+)', html)
        if im:
            infoid = im.group(1)
        else:
            m2 = re.search(r'/cn/(?:movie|tv)/(\d+)', path)
            if m2:
                infoid = m2.group(1)

        params = []
        mm = re.search(r'm3u8\s*=\s*\[([^\]]+)\]', html)
        if mm:
            params = re.findall(r'[\'"]([^\'"]+)[\'"]', mm.group(1))
        if not params:
            params = ['1080P']

        play_parts = []
        for p in params:
            name = f'第{p}集' if p.isdigit() else p
            m3u8 = f'{self.rhost}/info/m3u8/{infoid}/{p}.m3u8'
            play_parts.append(f'{name}${m3u8}')

        return {
            'list': [{
                'vod_id': path,
                'vod_name': title or infoid,
                'vod_pic': pic,
                'vod_content': title,
                'vod_play_from': 'PPnix',
                'vod_play_url': '#'.join(play_parts),
            }]
        }

    def searchContent(self, key, quick, pg="1"):
        pg = int(pg or 1)
        word = str(key).replace('-', ' ').strip()
        # /cn/search/{word}--.html
        path = f'/cn/search/{quote(word)}--.html'
        if pg > 1:
            path = f'/cn/search/{quote(word)}---{pg}-.html'
        html = self.fetch(self.rhost + path).text
        videos = self._parse_list(html)
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 20 else pg,
        }

    def playerContent(self, flag, id, vipFlags):
        play_url = str(id or '').strip()
        if play_url.startswith('/'):
            play_url = self.rhost + play_url
        if self.isVideoFormat(play_url):
            return {
                'parse': 0,
                'url': play_url,
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer': self.rhost + '/cn/',
                },
            }
        return {
            'parse': 1,
            'jx': '1',
            'url': play_url,
            'header': {
                'User-Agent': self.headers['User-Agent'],
                'Referer': self.rhost + '/cn/',
            },
        }

    def localProxy(self, param):
        pass
