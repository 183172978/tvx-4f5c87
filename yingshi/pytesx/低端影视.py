# coding=utf-8
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
低端影视 (ddys.pics)
风格对齐 可可影视.py
站点：https://ddys.pics
播放：详情页 switchSource / firstSource 直出 m3u8
"""
import re
import sys
from urllib.parse import quote

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider(object):
        pass

try:
    import requests
except ImportError:
    requests = None


def format_remarks(brand="低端影视", meta=""):
    clean = re.sub(r'[\r\n\t]+', ' ', str(meta or '')).strip()
    return '%s | %s' % (brand, clean) if clean else brand


class Spider(BaseSpider):
    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.host = 'https://ddys.pics'
        self.img_cdn = 'https://img.ddys.pics'
        self.ua = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.headers = {
            'User-Agent': self.ua,
            'Referer': self.host + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        }
        self.classes = [
            {'type_id': 'movie', 'type_name': '电影'},
            {'type_id': 'series', 'type_name': '剧集'},
            {'type_id': 'anime', 'type_name': '动漫'},
            {'type_id': 'variety', 'type_name': '综艺'},
        ]

    def init(self, extend=''):
        if extend and str(extend).startswith('http'):
            self.host = str(extend).rstrip('/')
            self.headers['Referer'] = self.host + '/'

    def getName(self):
        return '低端影视'

    def destroy(self):
        pass

    def isVideoFormat(self, url):
        if not url:
            return False
        u = str(url).lower()
        return any(x in u for x in ('.m3u8', '.mp4', '.flv', '.mkv'))

    def manualVideoCheck(self):
        return False

    def _get(self, url):
        if not url:
            return ''
        if not url.startswith('http'):
            url = self.host + (url if url.startswith('/') else '/' + url)
        try:
            if requests is None:
                import urllib.request
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
                    return r.read().decode('utf-8', 'ignore')
            r = requests.get(url, headers=self.headers, timeout=20, verify=False)
            r.encoding = 'utf-8'
            return r.text if r.status_code == 200 else ''
        except Exception as e:
            print('request error', url, e)
            return ''

    def _abs(self, path):
        if not path:
            return ''
        if path.startswith('http'):
            return path
        if path.startswith('//'):
            return 'https:' + path
        return self.host + (path if path.startswith('/') else '/' + path)

    def _parse_list(self, html):
        items = []
        seen = set()
        if not html:
            return items
        blocks = re.split(r'class="[^"]*movie-card[^"]*"', html)
        for b in blocks[1:]:
            hm = re.search(r'href="(/movie/[^"/]+)"', b)
            if not hm:
                continue
            path = hm.group(1).rstrip('/')
            if path in seen:
                continue
            seen.add(path)
            title = ''
            am = re.search(r'alt="([^"]+)"', b)
            if am:
                title = am.group(1).strip()
            if not title:
                tm = re.search(r'<h[23][^>]*>([^<]+)', b)
                if tm:
                    title = tm.group(1).strip()
            if not title:
                continue
            pic = ''
            im = re.search(r'(?:src|data-src)="(https?://[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"', b, re.I)
            if im:
                pic = im.group(1)
            note = ''
            nm = re.search(r'class="[^"]*(?:badge|tag|note|score)[^"]*"[^>]*>([^<]+)', b, re.I)
            if nm:
                note = nm.group(1).strip()
            items.append({
                'vod_id': path,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': format_remarks('低端影视', note),
                'style': {'type': 'rect', 'ratio': 0.75},
            })
        if not items:
            for m in re.finditer(r'href="(/movie/([^"/]+))"', html):
                path = m.group(1).rstrip('/')
                if path in seen:
                    continue
                seen.add(path)
                items.append({
                    'vod_id': path,
                    'vod_name': m.group(2).replace('-', ' '),
                    'vod_pic': '',
                    'vod_remarks': '低端影视',
                    'style': {'type': 'rect', 'ratio': 0.75},
                })
                if len(items) >= 40:
                    break
        return items

    def _extract_plays(self, html):
        play_from, play_url = [], []
        if not html:
            return play_from, play_url

        # switchSource(id, '第1集$url#第2集$url')
        calls = re.findall(r"switchSource\(\s*(\d+)\s*,\s*'((?:\\'|[^'])*)'\s*\)", html)
        labels = {}
        for m in re.finditer(
            r'<button[^>]*onclick="switchSource\((\d+)[^"]*"[^>]*>([\s\S]*?)</button>',
            html, re.I
        ):
            lab = re.sub(r'<[^>]+>', '', m.group(2))
            lab = re.sub(r'\s+', ' ', lab).strip()
            if lab:
                labels[m.group(1)] = lab

        seen = set()
        for sid, url_str in calls:
            url_str = url_str.replace('\\/', '/').replace("\\'", "'")
            if not url_str or url_str in seen:
                continue
            if '.m3u8' not in url_str and '.mp4' not in url_str:
                continue
            seen.add(url_str)
            name = labels.get(sid) or ('播放源' + sid)
            # 单集纯 url
            if url_str.startswith('http') and '#' not in url_str and '$' not in url_str:
                url_str = '正片$' + url_str
            play_from.append(name)
            play_url.append(url_str)

        if play_from:
            return play_from, play_url

        # firstSource JSON
        m = re.search(
            r'const\s+firstSource\s*=\s*(\{[^;]+\});',
            html
        )
        if m:
            try:
                import json
                obj = json.loads(m.group(1))
                u = (obj.get('url') or '').replace('\\/', '/')
                name = obj.get('name') or '播放源'
                q = obj.get('quality') or ''
                if q:
                    name = '%s (%s)' % (name, q)
                if u:
                    if u.startswith('http') and '#' not in u and '$' not in u:
                        u = '正片$' + u
                    play_from.append(name)
                    play_url.append(u)
            except Exception:
                pass

        if play_from:
            return play_from, play_url

        # 裸 m3u8
        m3s = re.findall(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*', html)
        uniq = []
        for u in m3s:
            u = u.replace('&amp;', '&')
            if u not in uniq and 'preview' not in u.lower():
                uniq.append(u)
        if uniq:
            play_from.append('直链')
            play_url.append('#'.join('播放%d$%s' % (i + 1, u) for i, u in enumerate(uniq[:20])))
        return play_from, play_url

    def homeContent(self, filter=False):
        return {'class': list(self.classes), 'filters': {}}

    def homeVideoContent(self):
        html = self._get(self.host + '/movie/')
        return {'list': self._parse_list(html)[:24]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = int(pg or 1)
        tid = str(tid or 'movie').strip('/')
        if page <= 1:
            url = '%s/%s/' % (self.host, tid)
        else:
            url = '%s/%s/page/%d/' % (self.host, tid, page)
        html = self._get(url)
        videos = self._parse_list(html)
        return {
            'list': videos,
            'page': page,
            'pagecount': page + 1 if len(videos) >= 12 else page,
            'limit': len(videos) or 24,
            'total': 9999,
        }

    def detailContent(self, ids):
        raw = ids[0] if isinstance(ids, (list, tuple)) else ids
        path = str(raw or '').strip()
        if not path:
            return {'list': []}
        if not path.startswith('/'):
            path = '/movie/' + path
        detail_url = self._abs(path)
        html = self._get(detail_url)
        if not html:
            return {'list': []}

        title = ''
        m = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', html, re.I)
        if m:
            title = re.sub(r'<[^>]+>', ' ', m.group(1))
            title = re.sub(r'\s+', ' ', title).strip()
        if not title:
            m = re.search(r'<title>([^<]+)', html, re.I)
            if m:
                title = m.group(1).split('_')[0].split('-')[0].strip()

        pic = ''
        m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html, re.I)
        if m:
            pic = m.group(1)
        if not pic:
            m = re.search(r'(https?://img\.ddys\.pics/[^"\']+\.(?:jpg|jpeg|png|webp))', html, re.I)
            if m:
                pic = m.group(1)

        desc = ''
        m = re.search(r'name=["\']description["\'][^>]*content=["\']([^"\']+)', html, re.I)
        if m:
            desc = m.group(1).strip()

        play_from, play_url = self._extract_plays(html)
        return {
            'list': [{
                'vod_id': path,
                'vod_name': title or path,
                'vod_pic': pic,
                'vod_remarks': '低端影视',
                'vod_content': desc,
                'vod_play_from': '$$$'.join(play_from) if play_from else '低端影视',
                'vod_play_url': '$$$'.join(play_url) if play_url else '',
            }]
        }

    def searchContent(self, key, quick, pg='1'):
        page = int(pg or 1)
        kw = quote(str(key or '').strip())
        if not kw:
            return {'list': []}
        url = '%s/search?q=%s' % (self.host, kw)
        if page > 1:
            url += '&page=%d' % page
        html = self._get(url)
        videos = self._parse_list(html)
        return {
            'list': videos,
            'page': page,
            'pagecount': page + 1 if len(videos) >= 12 else page,
            'limit': len(videos) or 24,
            'total': 9999,
        }

    def playerContent(self, flag, id, vipFlags=None):
        header = {
            'User-Agent': self.ua,
            'Referer': self.host + '/',
        }
        play = str(id or '').strip()
        if play.startswith('http') and self.isVideoFormat(play):
            return {'parse': 0, 'jx': 0, 'url': play, 'header': header}
        # 详情页路径兜底
        if play.startswith('/') or not play.startswith('http'):
            html = self._get(self._abs(play))
            pf, pu = self._extract_plays(html)
            if pu:
                first = pu[0].split('#')[0]
                if '$' in first:
                    first = first.split('$', 1)[-1]
                if first.startswith('http'):
                    return {'parse': 0, 'jx': 0, 'url': first, 'header': header}
        return {'parse': 0, 'jx': 0, 'url': play if play.startswith('http') else '', 'header': header}

    def localProxy(self, param):
        return None
