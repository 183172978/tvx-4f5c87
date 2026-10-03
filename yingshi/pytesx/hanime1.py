# -*- coding: utf-8 -*-
"""
Hanime1 (www.hanime1.my) - 热播APP风格
入口 /enter；分类 search?genre=；播放 source mp4 直链
"""
import json
import re
import sys

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
        self.host = 'https://www.hanime1.my'
        self.ua = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
        )
        self.classes = [
            {'type_id': 'home', 'type_name': '首页推荐'},
            {'type_id': '裏番', 'type_name': '里番'},
            {'type_id': '泡麵番', 'type_name': '泡面番'},
            {'type_id': '2D動畫', 'type_name': '2D动画'},
            {'type_id': 'Motion Anime', 'type_name': 'Motion Anime'},
            {'type_id': '3DCG', 'type_name': '3DCG'},
            {'type_id': '2.5D', 'type_name': '2.5D'},
            {'type_id': 'AI生成', 'type_name': 'AI生成'},
            {'type_id': 'MMD', 'type_name': 'MMD'},
            {'type_id': 'Cosplay', 'type_name': 'Cosplay'},
            {'type_id': '新番預告', 'type_name': '新番预告'},
        ]

    def getName(self):
        return 'Hanime1'

    def init(self, extend=''):
        pass

    def fetch(self, url, timeout=20):
        if requests is None:
            return None
        try:
            if url.startswith('/'):
                url = self.host + url
            r = requests.get(
                url,
                headers={
                    'User-Agent': self.ua,
                    'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
                    'Referer': self.host + '/enter',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                },
                timeout=timeout,
            )
            r.raise_for_status()
            r.encoding = r.apparent_encoding or 'utf-8'
            return r
        except Exception as e:
            print('fetch', url, e)
            return None

    def homeContent(self, filter):
        return {'class': self.classes, 'filters': {}}

    def homeVideoContent(self):
        r = self.fetch('/enter')
        if r is None:
            return {'list': []}
        return {'list': self._parse_list(r.text)[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = max(1, int(pg or 1))
        tid = str(tid or 'home')
        if tid == 'home':
            path = '/enter' if pg <= 1 else '/search?page=%d' % pg
        else:
            path = '/search?genre=%s' % requests.utils.quote(tid) if requests else '/search?genre=' + tid
            if pg > 1:
                path += '&page=%d' % pg
        r = self.fetch(path)
        videos = self._parse_list(r.text) if r is not None else []
        return {
            'list': videos,
            'page': pg,
            'pagecount': self._pagecount(r.text if r else '', pg, len(videos)),
            'limit': 40,
            'total': 9999,
        }

    def detailContent(self, ids):
        vid = re.sub(r'\D', '', str(ids[0] if isinstance(ids, (list, tuple)) else ids))
        r = self.fetch('/watch?v=' + vid)
        if r is None:
            return {'list': []}
        html = r.text
        name = vid
        m = re.search(r'<title>([^<]+)', html, re.I)
        if m:
            name = self._text(m.group(1).split('-')[0].split('|')[0])
            name = re.sub(r'H動漫.*', '', name, flags=re.I).strip() or name
        m = re.search(r'home-rows-videos-title[^>]*>\s*([^<]+)', html, re.I)
        if m:
            name = self._text(m.group(1)) or name
        pic = ''
        m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html, re.I)
        if m:
            pic = m.group(1)
        sources = self._parse_sources(html)
        play_url = '#'.join('%s$%s' % (s['label'], s['url']) for s in sources)
        return {
            'list': [{
                'vod_id': vid,
                'vod_name': name,
                'vod_pic': pic,
                'vod_content': name,
                'vod_remarks': sources[0]['label'] if sources else '',
                'vod_play_from': 'Hanime1',
                'vod_play_url': play_url or ('正片$' + self.host + '/watch?v=' + vid),
            }]
        }

    def searchContent(self, key, quick, pg='1'):
        pg = max(1, int(pg or 1))
        kw = str(key or '').strip()
        if not kw:
            return {'list': []}
        path = '/search?query=' + (requests.utils.quote(kw) if requests else kw)
        if pg > 1:
            path += '&page=%d' % pg
        r = self.fetch(path)
        videos = self._parse_list(r.text) if r is not None else []
        return {
            'list': videos,
            'page': pg,
            'pagecount': self._pagecount(r.text if r else '', pg, len(videos)),
        }

    def searchContentPage(self, key, quick, pg=1):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, id, vipFlags):
        url = str(id or '')
        hdr = {'User-Agent': self.ua, 'Referer': self.host + '/', 'Origin': self.host}
        if url.startswith('http') and any(x in url.lower() for x in ('.mp4', '.m3u8')):
            return {'parse': 0, 'url': url, 'header': hdr}
        vid = re.sub(r'\D', '', url) or url
        r = self.fetch('/watch?v=' + vid)
        if r is not None:
            sources = self._parse_sources(r.text)
            if sources:
                return {'parse': 0, 'url': sources[0]['url'], 'header': hdr}
        return {'parse': 1, 'url': self.host + '/watch?v=' + vid, 'header': hdr}

    def isVideoFormat(self, url):
        if not url:
            return False
        low = str(url).lower()
        return any(x in low for x in ('.mp4', '.m3u8'))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None

    def _text(self, s):
        s = str(s or '')
        for a, b in (
            ('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'),
            ('&quot;', '"'), ('&#39;', "'"), ('&nbsp;', ' '),
        ):
            s = s.replace(a, b)
        return re.sub(r'\s+', ' ', s).strip()

    def _parse_list(self, html):
        videos, seen = [], set()
        if not html:
            return videos
        # 首页 enter
        for m in re.finditer(
            r'href="[^"]*/watch\?v=(\d+)"[\s\S]{0,2000}?src="(https://[^"]+)"[\s\S]{0,600}?class="duration">\s*([^<]+)[\s\S]{0,800}?class="title"[^>]*>\s*([^<]+)',
            html,
            re.I,
        ):
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            videos.append({
                'vod_id': vid,
                'vod_name': self._text(m.group(4)),
                'vod_pic': m.group(2),
                'vod_remarks': self._text(m.group(3)),
            })
        # 搜索页
        for m in re.finditer(
            r'href="https?://[^"]*hanime1[^"]*/watch\?v=(\d+)"[\s\S]{0,2000}?src="(https://[^"]+)"[\s\S]{0,800}?home-rows-videos-title[^>]*>\s*([^<]+)',
            html,
            re.I,
        ):
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            videos.append({
                'vod_id': vid,
                'vod_name': self._text(m.group(3)),
                'vod_pic': m.group(2),
                'vod_remarks': '',
            })
        if not videos:
            for m in re.finditer(
                r'href="[^"]*/watch\?v=(\d+)"[\s\S]{0,1500}?src="(https://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                html,
                re.I,
            ):
                if m.group(1) in seen:
                    continue
                seen.add(m.group(1))
                videos.append({
                    'vod_id': m.group(1),
                    'vod_name': m.group(1),
                    'vod_pic': m.group(2),
                    'vod_remarks': '',
                })
        return videos

    def _parse_sources(self, html):
        lines, seen = [], set()
        for m in re.finditer(r'<source[^>]+src="(https://[^"]+)"[^>]*(?:size="(\d+)")?', html, re.I):
            url = m.group(1).replace('&amp;', '&')
            if url in seen:
                continue
            seen.add(url)
            size = m.group(2) or ''
            label = (size + 'P') if size else '正片'
            fm = re.search(r'-(\d{3,4})p', url, re.I)
            if fm:
                label = fm.group(1) + 'P'
                size = size or fm.group(1)
            lines.append({'label': label, 'url': url, 'size': int(size or 0)})
        lines.sort(key=lambda x: x['size'], reverse=True)
        return lines

    def _pagecount(self, html, page, n):
        mx = page
        for m in re.finditer(r'[?&]page=(\d+)', html or ''):
            p = int(m.group(1))
            if p > mx:
                mx = p
        if mx == page and n >= 20:
            return page + 1
        return mx


if __name__ == '__main__':
    sp = Spider()
    print(json.dumps(sp.homeContent(True), ensure_ascii=False)[:200])
    hv = sp.homeVideoContent()
    print('home', len(hv.get('list') or []), (hv.get('list') or [{}])[0].get('vod_name', '')[:40] if hv.get('list') else None)
    cat = sp.categoryContent('裏番', 1, {}, {})
    print('cat 裏番', len(cat.get('list') or []))
    if cat.get('list'):
        d = sp.detailContent([cat['list'][0]['vod_id']])
        print('detail', d['list'][0]['vod_name'][:40], d['list'][0]['vod_play_url'][:100])
        p = sp.playerContent('Hanime1', d['list'][0]['vod_id'], [])
        print('play', p.get('parse'), (p.get('url') or '')[:80])
    s = sp.searchContent('pure', False, 1)
    print('search', len(s.get('list') or []))
