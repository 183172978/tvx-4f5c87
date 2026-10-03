# -*- coding: utf-8 -*-
# 美女视频收藏馆 https://mnspscg.com/
# 按 post_list_li 切块解析，避免侧栏串数据
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
        return '美女视频收藏馆'

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return any(x in u for x in ('.mp4', '.m3u8', '.flv'))

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    rhost = 'https://mnspscg.com'
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'Referer': 'https://mnspscg.com/',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }

    cateManual = {
        '抖音': '2',
        'COS二次元': '5',
        '泳装海边': '6',
        '舞蹈视频': '7',
        '穿搭写真': '8',
        '日常随拍': '9',
        '未分类': '1',
    }

    def fetch(self, url, headers=None):
        import requests
        r = requests.get(url, headers=headers or self.headers, timeout=15)
        return r

    def homeContent(self, filter):
        classes = [{'type_name': k, 'type_id': v} for k, v in self.cateManual.items()]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        html = self.fetch(self.rhost + '/', headers=self.headers).text
        return {'list': self._parse_list(html)[:20]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = str(tid)
        if pg <= 1:
            url = f'{self.rhost}/category-{tid}.html'
        else:
            url = f'{self.rhost}/category-{tid}_{pg}.html'
        html = self.fetch(url, headers=self.headers).text
        videos = self._parse_list(html)
        has_next = f'category-{tid}_{pg + 1}.html' in html or len(videos) >= 8
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if has_next else pg,
            'limit': 20,
            'total': 99999,
        }

    def _parse_list(self, html):
        videos = []
        seen = set()
        if not html:
            return videos
        parts = re.split(r'class="[^"]*post_list_li[^"]*"', html, flags=re.I)
        for part in parts[1:]:
            if re.search(r'widget-post|sidebar', part[:120], re.I):
                continue
            hm = re.search(
                r'<h2>\s*<a\s+href="[^"]*?/post/(\d+)\.html"[^>]*>([^<]+)</a>',
                part,
                re.I,
            )
            if not hm:
                continue
            pid, title = hm.group(1), re.sub(r'\s+', ' ', hm.group(2)).strip()
            if pid in seen or not title:
                continue
            seen.add(pid)
            pic = ''
            dpm = re.search(r'pic\s*:\s*["\'](https?://[^"\']+)["\']', part, re.I)
            if dpm:
                pic = dpm.group(1)
            videos.append({
                'vod_id': pid,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': '',
            })
        if not videos:
            body = html
            main = re.search(
                r'class="[^"]*main-post[^"]*"([\s\S]+?)class="[^"]*sidebar',
                html,
                re.I,
            )
            if main:
                body = main.group(1)
            for m in re.finditer(
                r'<h2>\s*<a\s+href="[^"]*?/post/(\d+)\.html"[^>]*>([^<]+)</a>\s*</h2>',
                body,
                re.I,
            ):
                pid, title = m.group(1), re.sub(r'\s+', ' ', m.group(2)).strip()
                if pid in seen or not title:
                    continue
                seen.add(pid)
                videos.append({
                    'vod_id': pid,
                    'vod_name': title,
                    'vod_pic': '',
                    'vod_remarks': '',
                })
        return videos

    def detailContent(self, ids):
        pid = str(ids[0] if isinstance(ids, list) else ids).split('@@')[0]
        url = f'{self.rhost}/post/{pid}.html'
        html = self.fetch(url, headers=self.headers).text
        title = pid
        tm = re.search(r'<h1[^>]*>([^<]+)</h1>', html) or re.search(r'<title>([^<]+)</title>', html)
        if tm:
            title = tm.group(1).replace(' - 美女视频收藏馆', '').strip()
        pic = ''
        dpm = re.search(r'pic\s*:\s*["\'](https?://[^"\']+)["\']', html, re.I)
        if dpm:
            pic = dpm.group(1)
        type_name = ''
        cm = re.search(r'/category-\d+\.html">([^<]+)</a>', html)
        if cm:
            type_name = cm.group(1).strip()
        play = self._extract_play(html)
        return {
            'list': [{
                'vod_id': pid,
                'vod_name': title,
                'vod_pic': pic,
                'type_name': type_name,
                'vod_content': title,
                'vod_play_from': '直链' if play else '网页',
                'vod_play_url': f'正片${play}' if play else f'正片${url}',
            }]
        }

    def _extract_play(self, html):
        for pat in [
            r'url:\s*[\'"](https?://[^\'"]+\.mp4[^\'"]*)[\'"]',
            r'url:\s*[\'"](https?://[^\'"]+\.m3u8[^\'"]*)[\'"]',
            r'(https?://[^"\'\s]+/videos/[^"\'\s]+\.mp4)',
        ]:
            m = re.search(pat, html, re.I)
            if m:
                return m.group(1).replace('\\/', '/')
        return ''

    def searchContent(self, key, quick, pg="1"):
        pg = int(pg or 1)
        url = f'{self.rhost}/search.php?q={quote(key)}'
        if pg > 1:
            url += f'&page={pg}'
        html = self.fetch(url, headers=self.headers).text
        videos = self._parse_list(html)
        return {'list': videos, 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        play_url = str(id or '').strip()
        if 'mnspscg.com/post/' in play_url or play_url.isdigit():
            page = f'{self.rhost}/post/{play_url}.html' if play_url.isdigit() else play_url
            try:
                html = self.fetch(page, headers=self.headers).text
                direct = self._extract_play(html)
                if direct:
                    play_url = direct
            except Exception:
                pass
        if self.isVideoFormat(play_url):
            return {
                'parse': 0,
                'url': play_url,
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer': self.rhost + '/',
                },
            }
        return {
            'parse': 0,
            'url': play_url if play_url.startswith('http') else '',
            'header': {
                'User-Agent': self.headers['User-Agent'],
                'Referer': self.rhost + '/',
            },
        }

    def localProxy(self, param):
        pass
