# -*- coding: utf-8 -*-
"""
ptt01.com - 线上看
入口 /enter，Cookie x-index-auth=authed
分类 ?category_id=  详情 /{id}  集数 /{id}/{ep}
播放: 页面 source m3u8
"""
import json
import re
import sys
import urllib.parse

try:
    import requests
except ImportError:
    requests = None

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        def init(self, extend=''):
            pass


class Spider(BaseSpider):
    def __init__(self):
        self.host = 'https://ptt01.com'
        self.ua = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
        )
        self.cookie = 'x-index-auth=authed'
        self.classes = [
            {'type_id': '0', 'type_name': '最新'},
            {'type_id': '19', 'type_name': '大陆'},
            {'type_id': '20', 'type_name': '香港'},
            {'type_id': '81', 'type_name': '台湾'},
            {'type_id': '83', 'type_name': '日本'},
            {'type_id': '82', 'type_name': '韩国'},
            {'type_id': '22', 'type_name': '欧美'},
            {'type_id': '92', 'type_name': '泰国'},
            {'type_id': '23', 'type_name': '其他'},
        ]

    def getName(self):
        return 'ptt01'

    def init(self, extend=''):
        if extend and str(extend).startswith('http'):
            self.host = str(extend).rstrip('/')

    def get_header(self, url=None):
        return {
            'User-Agent': self.ua,
            'Referer': self.host + '/enter',
            'Cookie': self.cookie,
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }

    def fetch(self, url, timeout=20):
        if requests is None:
            return None
        try:
            if url.startswith('/'):
                url = self.host + url
            r = requests.get(url, headers=self.get_header(url), timeout=timeout)
            r.encoding = r.apparent_encoding or 'utf-8'
            return r
        except Exception as e:
            print('fetch', url, e)
            return None

    def homeContent(self, filter):
        return {'class': self.classes, 'filters': {}}

    def homeVideoContent(self):
        r = self.fetch('/enter')
        return {'list': self._parse_list(r.text if r is not None else '')[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = str(tid or '0')
        if tid == '0':
            url = '/enter' if pg <= 1 else ('/p/%d' % pg)
        else:
            url = '/?category_id=%s' % tid
            if pg > 1:
                url += '&page=%d' % pg
        r = self.fetch(url)
        videos = self._parse_list(r.text if r is not None else '')
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if len(videos) >= 20 else pg,
            'limit': 24,
            'total': 9999,
        }

    def searchContent(self, key, quick, pg='1'):
        pg = int(pg or 1)
        q = urllib.parse.quote(str(key or '').strip())
        url = '/node/search?q=%s' % q
        if pg > 1:
            url += '&page=%d' % pg
        r = self.fetch(url)
        return {
            'list': self._parse_list(r.text if r is not None else ''),
            'page': pg,
            'pagecount': pg + 1,
        }

    def searchContentPage(self, key, quick, pg=1):
        return self.searchContent(key, quick, pg)

    def detailContent(self, ids):
        vid = re.sub(r'\D', '', str(ids[0] if isinstance(ids, (list, tuple)) else ids))
        r = self.fetch('/' + vid)
        html = r.text if r is not None else ''
        name = vid
        m = re.search(r'<title>([^<]+)', html, re.I)
        if m:
            name = re.sub(r'\s+', ' ', m.group(1).split('-')[0].split(':')[0]).strip()
        pic = ''
        m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html, re.I)
        if m:
            pic = m.group(1)
        if not pic:
            m = re.search(r'thumbnailUrl["\']?\s*:\s*["\']([^"\']+)', html, re.I)
            if m:
                pic = m.group(1).replace('\\/', '/')
                if pic.startswith('/'):
                    pic = self.host + pic
        max_ep = 1
        for e in re.findall(r'/%s/(\d+)' % vid, html):
            n = int(e)
            if n > max_ep:
                max_ep = n
        m = re.search(r'第\s*(\d+)\s*集', html)
        if m and int(m.group(1)) > max_ep:
            max_ep = int(m.group(1))
        urls = ['第%d集$%s/%d' % (i, vid, i) for i in range(1, max_ep + 1)]
        return {
            'list': [{
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': pic,
                'vod_play_from': 'ptt01',
                'vod_play_url': '#'.join(urls),
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        path = str(id or '')
        if re.match(r'^\d+$', path):
            path = path + '/1'
        if not path.startswith('/'):
            path = '/' + path
        r = self.fetch(path)
        html = r.text if r is not None else ''
        url = ''
        m = re.search(r'<source[^>]+src="(https?://[^"]+\.m3u8[^"]*)"', html, re.I)
        if m:
            url = m.group(1)
        if not url:
            m = re.search(r'contentUrl["\']?\s*:\s*["\'](https?:\\?/\\?/[^"\']+\.m3u8[^"\']*)', html, re.I)
            if m:
                url = m.group(1).replace('\\/', '/')
        if not url:
            m = re.search(r'(https?://[^"\'\s]+\.m3u8[^"\'\s]*)', html, re.I)
            if m:
                url = m.group(1)
        return {
            'parse': 0,
            'url': url,
            'header': {
                'User-Agent': self.ua,
                'Referer': self.host + '/',
            },
        }

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4)(\?|$)', url or '', re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

    def destroy(self):
        pass

    def _parse_list(self, html):
        videos, seen = [], set()
        if not html:
            return videos
        for m in re.finditer(
            r'href="/(\d+)"[\s\S]{0,200}?src="(https?://[^"]+)"[\s\S]{0,500}?fa-play-circle[^>]*></i>([\s\S]*?)</a>',
            html,
            re.I,
        ):
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            name = re.sub(r'<[^>]+>', '', m.group(3)).strip()
            if not name:
                continue
            remark = ''
            slice_ = html[max(0, m.start() - 200): m.start() + 200]
            em = re.search(r'共\s*\d+\s*集|第\s*\d+\s*集', slice_)
            if em:
                remark = re.sub(r'\s+', '', em.group(0))
            videos.append({
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': m.group(2),
                'vod_remarks': remark,
            })
        if not videos:
            for m in re.finditer(
                r'href="/(\d+)"[^>]*>[\s\S]{0,300}?fa-play-circle[^>]*></i>([\s\S]*?)</a>',
                html,
                re.I,
            ):
                if m.group(1) in seen:
                    continue
                seen.add(m.group(1))
                name = re.sub(r'<[^>]+>', '', m.group(2)).strip()
                if name:
                    videos.append({
                        'vod_id': m.group(1),
                        'vod_name': name,
                        'vod_pic': '',
                        'vod_remarks': '',
                    })
        return videos


if __name__ == '__main__':
    sp = Spider()
    print(json.dumps(sp.homeContent(True), ensure_ascii=False)[:150])
    r = sp.categoryContent('0', 1, False, {})
    print('list', len(r.get('list') or []))
    if r.get('list'):
        print('first', r['list'][0])
        d = sp.detailContent([r['list'][0]['vod_id']])
        print('detail', (d.get('list') or [{}])[0].get('vod_name'), (d.get('list') or [{}])[0].get('vod_play_url', '')[:80])
        p = sp.playerContent('ptt01', r['list'][0]['vod_id'] + '/1', None)
        print('play', str(p.get('url'))[:100])
